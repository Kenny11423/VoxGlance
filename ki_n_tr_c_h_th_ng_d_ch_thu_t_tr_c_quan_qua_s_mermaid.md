# Hệ thống Dịch thuật Trực quan & Phụ đề Âm thanh Thời gian thực (OmniTranslate)
## Tổng hợp Sơ đồ Kỹ thuật (Mermaid Markdown)

Tài liệu này chứa 5 sơ đồ kiến trúc hoàn chỉnh được chuẩn hóa bằng cú pháp **Mermaid**. Bạn có thể sao chép trực tiếp vào GitHub README, Notion, Obsidian hoặc các công cụ hỗ trợ Markdown.

---

### Sơ đồ 1: Luồng dữ liệu Hợp nhất Thời gian thực (End-to-End Realtime Pipeline)

Sơ đồ mô tả quy trình tiếp nhận đồng thời hai luồng Âm thanh (Audio) và Hình ảnh (Visual), xử lý phân tán qua các mô hình AI tối ưu và hội tụ tại bộ điều phối né va chạm trước khi đẩy ra màn hình.

```mermaid
flowchart TD
    subgraph HostSystem ["Hệ thống Nguồn / OS Loopback"]
        AudioIn["System Audio Output\n(WASAPI / PipeWire 16kHz PCM)"]
        ScreenIn["Screen Desktop Buffer\n(DXGI / Desktop Duplication)"]
    end

    subgraph AudioPipeline ["Luồng Xử lý Âm thanh (Audio Pipeline)"]
        RingBuf["Ring Buffer Audio\n(Chunk 250ms)"]
        VAD{"Silero VAD\n(Voice Detection)"}
        DropSilent["Drop Chunk / Tiết kiệm GPU"]
        WhisperASR["Streaming Faster-Whisper INT8\n(CTranslate2 CUDA:0)"]
        SimulMT["Simultaneous MT Engine\n(Wait-k Policy / CTranslate2)"]
        SubStream["Audio Subtitle Stream\n(Tokens + Word Timestamps)"]

        RingBuf --> VAD
        VAD -- "Im lặng / Nhạc nền" --> DropSilent
        VAD -- "Có tiếng nói" --> WhisperASR
        WhisperASR --> SimulMT
        SimulMT --> SubStream
    end

    subgraph VisualPipeline ["Luồng Xử lý Thị giác (Visual OCR Pipeline)"]
        DiffFilter{"Frame Difference / SSIM\n(Biến thiên > 5%?)"}
        SkipFrame["Skip Frame / Idle"]
        DBNet["Text Detection: DBNet\n(TensorRT FP16)"]
        CacheCheck{"LRU Cache Check\n(Trùng lặp UI?)"}
        CacheHit["Cache Hit: Trả kết quả tức thì"]
        CRNNRec["Text Recognition: SVTR/CRNN\n(TensorRT INT8)"]
        VisualMT["NMT / Context-aware Translation"]
        VisualStream["Visual Boxes Stream\n(Coordinates + Translated Text)"]

        DiffFilter -- "Không đổi" --> SkipFrame
        DiffFilter -- "Màn hình đổi" --> DBNet
        DBNet --> CacheCheck
        CacheCheck -- "Đã có trong Cache" --> CacheHit
        CacheCheck -- "Ký tự mới" --> CRNNRec
        CRNNRec --> VisualMT
        VisualMT --> VisualStream
        CacheHit --> VisualStream
    end

    subgraph Orchestrator ["Bộ Điều phối & Lớp phủ Hiển thị"]
        Resolver{"Conflict & Collision Resolver\n(Kiểm tra va chạm tọa độ)"}
        OverlayUI["Transparent Overlay (PyQt6 Direct2D)\n- Subtitle cuộn mượt (Roll-up)\n- Thay thế chữ đè (Inpainting/Overlay)\n- Click-through (WS_EX_TRANSPARENT)"]

        Resolver --> OverlayUI
    end

    AudioIn --> RingBuf
    ScreenIn --> DiffFilter
    SubStream --> Resolver
    VisualStream --> Resolver
```

---

### Sơ đồ 2: Cấu trúc Đa tiến trình & IPC (Multi-Process & IPC Architecture)

Minh họa việc cô lập tiến trình để vượt qua rào cản Python GIL, bảo vệ độ mượt 60 FPS của giao diện Overlay và tối ưu việc truyền nhận dữ liệu lớn qua Shared Memory.

```mermaid
graph TD
    subgraph MainDaemonProcess ["Tiến trình Điều phối Chính (Main Daemon Process)"]
        Lifecycle["Quản lý Vòng đời & Config Store"]
        Hotkeys["Global Hotkeys Listener (Windows Hook)"]
        ProfileMgr["App Profile Manager (Auto Detect Process)"]
    end

    subgraph AIWorkerProcess ["Tiến trình Tính toán AI (GPU Dedicated Process)"]
        AudioWorker["WASAPI Loopback Capture Worker"]
        DXGIWorker["DXGI Desktop Duplication Worker"]
        WhisperWorker["Faster-Whisper INT8 (CUDA:0)"]
        TRTWorker["PaddleOCR TensorRT Engine"]
        LRUCacheWorker["In-Memory LRU Termbase Cache"]
    end

    subgraph UIOverlayProcess ["Tiến trình Giao diện Lớp phủ (UI Overlay Process)"]
        PyQtEngine["PyQt6 / QPainter 60 FPS Render Loop"]
        ClickThroughEngine["Click-Through & Win32 Layered Handler"]
        FloatingWidget["Mini Floating Pill Widget"]
        SubRenderer["Smooth Word-by-Word Subtitle Engine"]
    end

    MainDaemonProcess -- "Spawn & Giám sát Heathcheck" --> AIWorkerProcess
    MainDaemonProcess -- "Spawn & Giám sát Heathcheck" --> UIOverlayProcess

    AIWorkerProcess <-- "Named Pipes / Unix Socket\n(Control Commands & State Sync)" --> MainDaemonProcess
    MainDaemonProcess <-- "IPC Control Signals\n(Hotkeys: Alt+T, Alt+S)" --> UIOverlayProcess

    AIWorkerProcess -- "IPC Unix Socket / Fast Pipe\n(Subtitle Tokens & Timestamps)" --> UIOverlayProcess
    AIWorkerProcess -- "POSIX Shared Memory (shm)\n(Raw Frames & Bounding Box Coordinates)" --> UIOverlayProcess
```

---

### Sơ đồ 3: Phân bổ Bộ nhớ GPU & Giới hạn VRAM (< 1GB Target)

Mô tả cơ chế cấp phát tĩnh và chia sẻ CUDA Context giữa Whisper và TensorRT nhằm đảm bảo không phát sinh phân mảnh bộ nhớ và kiểm soát trần VRAM dưới 950MB.

```mermaid
graph TB
    subgraph TotalVRAM ["TỔNG BỘ NHỚ VRAM MỤC TIÊU: < 1000 MB (Card 4GB)"]
        direction TB

        subgraph WhisperSegment ["1. Phân vùng Faster-Whisper (~380 MB)"]
            W_Weights["Weights INT8: ~250 MB"]
            W_KV["Decoder KV Cache: ~80 MB"]
            W_Work["Workspace Scratch: ~50 MB"]
        end

        subgraph TRTSegment ["2. Phân vùng TensorRT OCR (~270 MB)"]
            TRT_Det["DBNet Det Engine: ~90 MB"]
            TRT_Rec["SVTR Rec Engine: ~60 MB"]
            TRT_Work["Capped Workspace Size: ~120 MB"]
        end

        subgraph SharedSegment ["3. Bộ nhớ Dịch thuật & CUDA Core (~150 MB)"]
            NMTCache["CTranslate2 NMT / Prompt Context: ~150 MB\n(Hoặc 0 MB nếu dùng Cloud API)"]
        end

        subgraph ReservedSegment ["4. Vùng đệm Dự phòng An toàn (~150 MB)"]
            CUDA_Overhead["CUDA Context Overhead & Peak Guard Buffer\n(Ngăn chặn Crash do OOM)"]
        end
    end

    SharedPool["Shared CUDA Stream & Arena Allocator\n(arena_extend_strategy = kSameAsRequested)"]
    SharedPool -.-> WhisperSegment
    SharedPool -.-> TRTSegment
    SharedPool -.-> SharedSegment
```

---

### Sơ đồ 4: Thuật toán Stream-and-Revise (Giảm delay phụ đề âm thanh)

Diễn giải trực quan cơ chế sinh phụ đề tạm thời (Partial Tokens) và cập nhật ngữ nghĩa (Commit) tương tự YouTube Live Caption.

```mermaid
sequenceDiagram
    autonumber
    actor Speaker as Người Nói / Video Audio
    participant VAD as Silero VAD (30ms Frame)
    participant ASR as Faster-Whisper Streaming
    participant MT as Simultaneous MT (Wait-k)
    participant UI as Transparent Overlay (UI)

    Speaker->>VAD: Bắt đầu nói: "Hôm nay..." (0 - 250ms)
    VAD->>ASR: Gửi Audio Chunk 1
    ASR->>MT: Trả Partial Text: "Hôm..."
    MT->>UI: Render chữ mờ/nhấp nháy: "Hôm..."

    Speaker->>VAD: Tiếp tục nói: "...chúng ta làm..." (250 - 500ms)
    VAD->>ASR: Gửi Audio Chunk 2
    ASR->>MT: Cập nhật Partial Text: "Hôm nay chúng..."
    MT->>UI: Sửa và hiển thị tức thì (Revise): "Hôm nay chúng..."

    Speaker->>VAD: Tiếp tục nói: "...dự án này." (500 - 850ms)
    VAD->>ASR: Gửi Audio Chunk 3
    ASR->>MT: Cập nhật Partial Text: "Hôm nay chúng ta làm dự án này"
    MT->>UI: Sửa và hiển thị tức thì (Revise): "Hôm nay chúng ta làm dự án này"

    Speaker->>VAD: Ngắt hơi / Khoảng lặng (> 200ms)
    VAD->>ASR: Tín hiệu Silence Cut (End of Thought)
    ASR->>MT: Commit Final Tokens + Word Timestamps
    MT->>UI: Chốt hạ văn bản (Commit): Khóa màu chữ rõ nét
    UI->>UI: Kích hoạt hiệu ứng trôi dòng lên (Roll-up Subtitle)
```

---

### Sơ đồ 5: Kiến trúc Lớp phủ Màn hình & Cơ chế Click-Through (UI Overlay)

Sơ đồ trạng thái hiển thị của lớp phủ màn hình, giải thích cách giải quyết xung đột không gian giữa Text Box OCR và Thanh phụ đề âm thanh.

```mermaid
stateDiagram-v2
    [*] --> IdleListening: Khởi chạy Ứng dụng & Ghim Top-Most

    state IdleListening {
        [*] --> PollingBackground
        PollingBackground: Cửa sổ trong suốt ghim trên cùng
        PollingBackground: Cờ Win32 WS_EX_TRANSPARENT | WS_EX_LAYERED
        PollingBackground: Chuột click xuyên qua không mất Focus game/app
    }

    IdleListening --> AudioActive: VAD phát hiện có giọng nói
    IdleListening --> VisualActive: SSIM phát hiện màn hình thay đổi

    state AudioActive {
        RenderSubBottom: Hiển thị Subtitle ở vị trí mặc định (Đáy màn hình - 85% H)
        CheckCollision: Kiểm tra va chạm với Box OCR
    }

    state VisualActive {
        DetectBoxes: Tìm tọa độ Bounding Box (X, Y, W, H)
        RenderOCRBox: Vẽ Box đè lên chữ gốc (Inpainting + Text Outline)
    }

    AudioActive --> CollisionHandling: Tọa độ Subtitle trùng với Bounding Box OCR
    state CollisionHandling {
        RelocateSubtitle: Đẩy Subtitle tạm thời lên đỉnh màn hình (Top - 10% H)
    }

    CollisionHandling --> NormalState: Box OCR hết hạn hoặc biến mất
    state NormalState {
        ResetPosition: Đưa Subtitle trôi mượt về lại vị trí đáy (Bottom)
    }

    AudioActive --> IdleListening: Hết câu + Subtitle timeout
    VisualActive --> IdleListening: Màn hình không đổi + Hết thời gian giữ Box
```

---

### Bảng tóm tắt cú pháp và công cụ hỗ trợ

| Nền tảng | Cách render | Ghi chú |
| :--- | :--- | :--- |
| **GitHub** | Tự động render trong khối ```` ```mermaid ```` | Hỗ trợ đầy đủ Flowchart, Sequence, StateDiagram |
| **Notion** | Chọn block dạng **Code** $\rightarrow$ Đổi ngôn ngữ sang **Mermaid** | Hiển thị sơ đồ dạng interactive trực quan |
| **Obsidian** | Bao quanh bằng khối ```` ```mermaid ```` | Render native với khả năng zoom/pan mượt mà |
| **GitBook** | Hỗ trợ trực tiếp thông qua Mermaid extension | Phù hợp làm trang Developer Documentation |