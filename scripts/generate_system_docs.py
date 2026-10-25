#!/usr/bin/env python3
"""Script generate professional Microsoft Word (.docx) document for System Analysis & Use Case Specification."""

import os
import subprocess
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = WORKSPACE_DIR / "docs"
ASSETS_DIR = DOCS_DIR / "assets"
DOCX_PATH = DOCS_DIR / "Bao_Cao_Phan_Tich_He_Thong_Va_Use_Case.docx"

ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def generate_fdd_image() -> Path:
    """Generate high-resolution PNG for Functional Decomposition Diagram."""
    dot_content = """
    digraph FDD {
        graph [rankdir=TB, splines=ortho, nodesep=0.4, ranksep=0.6, bgcolor="transparent"];
        node [fontname="Arial", fontsize=10, shape=box, style="filled,rounded", margin="0.15,0.1"];
        edge [color="#475569", penwidth=1.2, arrowhead=none];

        // Root
        ROOT [label="HỆ THỐNG DỊCH THUẬT ĐA PHƯƠNG THỨC THỜI GIAN THỰC\\n(Real-Time In-Place Multimodal Translator)", 
              fillcolor="#1E3A8A", fontcolor="#FFFFFF", fontsize=12, penwidth=2, color="#172554"];

        // Level 1 Subsystems
        F1 [label="1.0 QUẢN TRỊ & ĐIỀU PHỐI HỆ THỐNG", fillcolor="#2563EB", fontcolor="#FFFFFF", fontsize=11, penwidth=1.5, color="#1D4ED8"];
        F2 [label="2.0 DỊCH THUẬT TRỰC QUAN MÀN HÌNH", fillcolor="#2563EB", fontcolor="#FFFFFF", fontsize=11, penwidth=1.5, color="#1D4ED8"];
        F3 [label="3.0 DỊCH THUẬT ÂM THANH TRỰC TIẾP", fillcolor="#2563EB", fontcolor="#FFFFFF", fontsize=11, penwidth=1.5, color="#1D4ED8"];
        F4 [label="4.0 ĐỘNG CƠ DỊCH THUẬT ĐA NGÔN NGỮ", fillcolor="#2563EB", fontcolor="#FFFFFF", fontsize=11, penwidth=1.5, color="#1D4ED8"];
        F5 [label="5.0 GIAO DIỆN & LỚP PHỦ XUYÊN THẤU", fillcolor="#2563EB", fontcolor="#FFFFFF", fontsize=11, penwidth=1.5, color="#1D4ED8"];

        ROOT -> F1;
        ROOT -> F2;
        ROOT -> F3;
        ROOT -> F4;
        ROOT -> F5;

        // Level 2 - F1
        node [fillcolor="#EFF6FF", fontcolor="#0F172A", color="#93C5FD", penwidth=1];
        F11 [label="1.1 Khởi tạo cấu hình (YAML/CLI)"];
        F12 [label="1.2 Quản trị VRAM (OOM Guard Buffer)"];
        F13 [label="1.3 Quản lý bộ đệm thuật ngữ (LRU Cache)"];
        F14 [label="1.4 Điều phối luồng Orchestrator Pipeline"];
        F1 -> F11; F1 -> F12; F1 -> F13; F1 -> F14;

        // Level 2 - F2
        F21 [label="2.1 Chụp màn hình (Full Screen / ROI Slurp)"];
        F22 [label="2.2 Phát hiện cuộn (Clear-on-Scroll 3.5%)"];
        F23 [label="2.3 Nhận dạng chữ (RapidOCR ONNX Runtime)"];
        F24 [label="2.4 Lọc nhiễu ký tự & Loại bỏ chữ ma"];
        F25 [label="2.5 Ghép dòng thông minh (Sentence Stitcher)"];
        F26 [label="2.6 Hòa sắc & Co giãn font gốc (Aesthetic)"];
        F2 -> F21; F2 -> F22; F2 -> F23; F2 -> F24; F2 -> F25; F2 -> F26;

        // Level 2 - F3
        F31 [label="3.1 Thu âm Mic & Desktop Loopback"];
        F32 [label="3.2 Lọc hoạt tính giọng nói (Silero VAD)"];
        F33 [label="3.3 Nhận dạng trực tiếp (Faster-Whisper)"];
        F34 [label="3.4 Xử lý phụ đề 2 dòng (2-Line Roll-Up)"];
        F3 -> F31; F3 -> F32; F3 -> F33; F3 -> F34;

        // Level 2 - F4
        F41 [label="4.1 Dịch GPU song song (CTranslate2 <40ms)"];
        F42 [label="4.2 Dịch đám mây dự phòng (Cloud Fallback)"];
        F43 [label="4.3 Quản lý từ điển & Thuật ngữ riêng"];
        F4 -> F41; F4 -> F42; F4 -> F43;

        // Level 2 - F5
        F51 [label="5.1 Lớp phủ xuyên thấu chuột 60 FPS"];
        F52 [label="5.2 Chống đè/va chạm (Collision Resolver)"];
        F53 [label="5.3 Thanh điều khiển nổi (Floating Toolbar)"];
        F54 [label="5.4 Quản lý phím tắt nhanh (F9, Esc, R)"];
        F5 -> F51; F5 -> F52; F5 -> F53; F5 -> F54;
    }
    """
    dot_file = ASSETS_DIR / "fdd_diagram.dot"
    png_file = ASSETS_DIR / "fdd_diagram.png"
    dot_file.write_text(dot_content, encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=250", str(dot_file), "-o", str(png_file)], check=True)
    return png_file


def generate_usecase_image() -> Path:
    """Generate high-resolution PNG for General Use Case Diagram."""
    dot_content = """
    digraph UseCaseDiagram {
        graph [rankdir=LR, nodesep=0.35, ranksep=0.7, bgcolor="transparent"];
        node [fontname="Arial", fontsize=10];
        edge [fontname="Arial", fontsize=9, color="#475569"];

        // Actors
        node [shape=box, style="filled,rounded", penwidth=1.5];
        User [label="<<Actor>>\\nNgười dùng cuối\\n(End-User)", fillcolor="#DBEAFE", color="#1D4ED8", fontcolor="#1E3A8A"];
        OS_Display [label="<<Actor>>\\nDisplay Server\\n(Wayland / X11)", fillcolor="#FEF3C7", color="#D97706", fontcolor="#92400E"];
        OS_Audio [label="<<Actor>>\\nAudio Subsystem\\n(PipeWire / Pulse)", fillcolor="#FEF3C7", color="#D97706", fontcolor="#92400E"];
        GPU_HW [label="<<Actor>>\\nGPU & Driver\\n(CUDA / NVML)", fillcolor="#DCFCE7", color="#16A34A", fontcolor="#166534"];
        Cloud_MT [label="<<Actor>>\\nCloud MT API\\n(Google / DeepL)", fillcolor="#F3E8FF", color="#9333EA", fontcolor="#6B21A8"];

        // System Boundary
        subgraph cluster_System {
            label = "HỆ THỐNG DỊCH THUẬT ĐA PHƯƠNG THỨC THỜI GIAN THỰC";
            fontname = "Arial Bold";
            fontsize = 12;
            fontcolor = "#1E293B";
            style = "filled,rounded";
            fillcolor = "#F8FAFC";
            color = "#94A3B8";
            penwidth = 1.5;

            node [shape=ellipse, style="filled", fillcolor="#FFFFFF", color="#0284C7", penwidth=1.2, fontcolor="#0F172A", margin="0.1,0.05"];

            // Primary Use Cases
            UC_Visual [label="UC-01: Dịch màn hình tại chỗ\\n(In-Place Visual Translation)", penwidth=2, color="#0369A1", fillcolor="#E0F2FE"];
            UC_Audio [label="UC-03: Dịch phụ đề âm thanh\\n(Live Audio Subtitle)", penwidth=2, color="#0369A1", fillcolor="#E0F2FE"];
            UC_Snap [label="UC-04: Dịch tức thì (F9)"];
            UC_ROI [label="UC-05: Kéo chọn vùng (R)"];
            UC_Toggle [label="UC-06: Ẩn/Hiện lớp phủ (Esc)"];
            UC_Guard [label="UC-07: Giám sát VRAM & OOM"];

            // Sub-Use Cases
            UC_ClearScroll [label="UC-02: Tự động xóa khi cuộn\\n(Clear-on-Scroll)"];
            UC_CapScreen [label="Chụp khung hình"];
            UC_OCR [label="Nhận diện & Lọc rác OCR"];
            UC_Aesthetic [label="Lấy màu nền & Co giãn font"];
            UC_CapAudio [label="Thu âm thanh Mic/Loopback"];
            UC_ASR [label="Lọc VAD & Nhận dạng Whisper"];
            UC_SubRoll [label="Hiển thị phụ đề 2 dòng & Tránh đè"];
            UC_Translate [label="Dịch đa ngôn ngữ CTranslate2 GPU"];
            UC_Cloud [label="Dịch dự phòng Cloud API"];
        }

        // User Associations
        User -> UC_Visual [penwidth=1.5, color="#1D4ED8"];
        User -> UC_Audio [penwidth=1.5, color="#1D4ED8"];
        User -> UC_Snap [penwidth=1.2, color="#1D4ED8"];
        User -> UC_ROI [penwidth=1.2, color="#1D4ED8"];
        User -> UC_Toggle [penwidth=1.2, color="#1D4ED8"];

        // System Actor Associations
        UC_CapScreen -> OS_Display [penwidth=1.2, color="#D97706", dir=both];
        UC_ROI -> OS_Display [penwidth=1.2, color="#D97706", dir=both];
        UC_CapAudio -> OS_Audio [penwidth=1.2, color="#D97706", dir=both];
        UC_Guard -> GPU_HW [penwidth=1.2, color="#16A34A", dir=both];
        UC_Translate -> GPU_HW [penwidth=1.2, color="#16A34A"];
        UC_ASR -> GPU_HW [penwidth=1.2, color="#16A34A"];
        UC_Cloud -> Cloud_MT [penwidth=1.2, color="#9333EA", dir=both];

        // Include & Extend Relationships
        edge [style=dashed, penwidth=1.0, color="#64748B", arrowhead=open];
        UC_Visual -> UC_CapScreen [label="<<include>>"];
        UC_Visual -> UC_OCR [label="<<include>>"];
        UC_Visual -> UC_Aesthetic [label="<<include>>"];
        UC_Visual -> UC_Translate [label="<<include>>"];

        UC_Audio -> UC_CapAudio [label="<<include>>"];
        UC_Audio -> UC_ASR [label="<<include>>"];
        UC_Audio -> UC_Translate [label="<<include>>"];
        UC_Audio -> UC_SubRoll [label="<<include>>"];

        UC_ClearScroll -> UC_Visual [label="<<extend>>"];
        UC_Snap -> UC_Visual [label="<<extend>>"];
        UC_ROI -> UC_Visual [label="<<extend>>"];
        UC_Cloud -> UC_Translate [label="<<extend\\n(fallback)>>"];
    }
    """
    dot_file = ASSETS_DIR / "usecase_diagram.dot"
    png_file = ASSETS_DIR / "usecase_diagram.png"
    dot_file.write_text(dot_content, encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=250", str(dot_file), "-o", str(png_file)], check=True)
    return png_file


def set_cell_shading(cell, color_hex: str):
    """Set background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{color_hex}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    """Set inner padding for table cell (in dxa: 20 dxa = 1 pt)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def format_table(table, header_bg="1E3A8A", alt_row_bg="F8FAFC"):
    """Apply professional styling to table."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header row
    for cell in table.rows[0].cells:
        set_cell_shading(cell, header_bg)
        set_cell_margins(cell, top=160, bottom=160, left=180, right=180)
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.name = "Arial"

    # Data rows
    for r_idx, row in enumerate(table.rows[1:], start=1):
        bg = alt_row_bg if r_idx % 2 == 1 else "FFFFFF"
        for cell in row.cells:
            set_cell_shading(cell, bg)
            set_cell_margins(cell, top=130, bottom=130, left=160, right=160)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.name = "Arial"
                    run.font.size = Pt(9.5)


def build_docx_document(fdd_png: Path, usecase_png: Path):
    """Build the complete professional Word document."""
    doc = docx.Document()

    # Page Margins: 1 inch (72 pt)
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    # Base Styles
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Arial"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)

    # Document Header / Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(4)
    run_sub = p_title.add_run("BÁO CÁO PHÂN TÍCH & THIẾT KẾ HỆ THỐNG PHẦN MỀM\n")
    run_sub.font.size = Pt(13)
    run_sub.font.bold = True
    run_sub.font.color.rgb = RGBColor(71, 85, 105)

    run_main = p_title.add_run("HỆ THỐNG DỊCH THUẬT ĐA PHƯƠNG THỨC THỜI GIAN THỰC\n(REAL-TIME IN-PLACE MULTIMODAL TRANSLATOR)")
    run_main.font.size = Pt(18)
    run_main.font.bold = True
    run_main.font.color.rgb = RGBColor(30, 58, 138)

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_after = Pt(20)
    run_meta = p_meta.add_run("Tài liệu: Đặc tả Actors, Phân cấp Chức năng (FDD) & Mô hình Use Case Tổng quát\nPhiên bản: 1.0  |  Ngày lập: 20/10/2026")
    run_meta.font.size = Pt(9.5)
    run_meta.font.italic = True
    run_meta.font.color.rgb = RGBColor(100, 116, 139)

    # Horizontal Rule
    p_hr = doc.add_paragraph()
    p_hr.paragraph_format.space_after = Pt(16)
    p_hr_border = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="1" w:color="2563EB"/></w:pBdr>')
    p_hr._p.get_or_add_pPr().append(p_hr_border)

    # =========================================================================
    # PHẦN 1: XÁC ĐỊNH CÁC ACTOR
    # =========================================================================
    h1 = doc.add_heading(level=1)
    r1 = h1.add_run("1. Xác Định Các Actor (Tác Nhân Tham Gia Hệ Thống)")
    r1.font.color.rgb = RGBColor(30, 58, 138)
    r1.font.bold = True

    p_intro_actor = doc.add_paragraph(
        "Hệ thống Dịch thuật Đa phương thức Thời gian thực tương tác với 1 Tác nhân người dùng chính "
        "(Primary Actor) và 4 Tác nhân hệ thống/phần cứng/dịch vụ ngoài (Secondary/Supporting Actors) "
        "để tạo nên trải nghiệm dịch mượt mà, độc lập và bảo mật cao:"
    )
    p_intro_actor.paragraph_format.space_after = Pt(10)

    # Table of Actors
    actor_table = doc.add_table(rows=6, cols=4)
    actor_headers = ["STT", "Actor (Tác nhân)", "Phân loại", "Mô tả Vai trò & Trách nhiệm"]
    for c_idx, title in enumerate(actor_headers):
        actor_table.rows[0].cells[c_idx].paragraphs[0].text = title

    actor_data = [
        ("1", "Người dùng cuối\n(End-User)", "Primary Actor\n(Con người)",
         "Chơi game ngoại ngữ, đọc tài liệu/web novel/manga, xem video hội thảo. Kích hoạt/dừng dịch, chọn vùng quét màn hình (ROI), dịch nhanh (F9), ẩn/hiện lớp phủ (Esc)."),
        ("2", "Máy chủ Hiển thị OS\n(Display Server)", "Secondary Actor\n(Hệ thống OS)",
         "Wayland (Hyprland/Sway), X11 (XCB), Windows DWM. Cung cấp luồng chụp màn hình framebuffer (grim, mss), hỗ trợ cửa sổ trong suốt xuyên thấu chuột (XShape click-through) và ghim Always-on-Top."),
        ("3", "Phân hệ Âm thanh OS\n(Audio Subsystem)", "Secondary Actor\n(Hệ thống OS)",
         "PipeWire, PulseAudio, Windows WASAPI. Cung cấp luồng thu âm thanh Microphone trực tiếp và âm thanh phát ra trong máy (Desktop Audio Loopback)."),
        ("4", "Phần cứng & Driver GPU\n(NVIDIA / NVML)", "Secondary Actor\n(Phần cứng)",
         "GPU và NVIDIA Driver quản trị VRAM, hỗ trợ tăng tốc phần cứng Tensor/CUDA cho các mô hình suy luận AI: Faster-Whisper ASR, RapidOCR và CTranslate2 MT."),
        ("5", "Dịch vụ Đám mây\n(Cloud MT API)", "Secondary Actor\n(Dịch vụ ngoại vi)",
         "Google Translate API, DeepL API. Đóng vai trò cổng dịch dự phòng (Fallback Translator) khi người dùng kích hoạt hoặc khi mô hình AI Offline cần bổ trợ.")
    ]

    for r_idx, row_data in enumerate(actor_data, start=1):
        for c_idx, val in enumerate(row_data):
            actor_table.rows[r_idx].cells[c_idx].paragraphs[0].text = val

    # Set Column Widths
    col_widths = [Inches(0.6), Inches(1.8), Inches(1.4), Inches(2.7)]
    for row in actor_table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

    format_table(actor_table, header_bg="1E3A8A")
    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # =========================================================================
    # PHẦN 2: BIỂU ĐỒ PHÂN CẤP CHỨC NĂNG (FDD)
    # =========================================================================
    h2 = doc.add_heading(level=1)
    r2 = h2.add_run("2. Biểu Đồ Phân Cấp Chức Năng (Functional Decomposition Diagram - FDD)")
    r2.font.color.rgb = RGBColor(30, 58, 138)
    r2.font.bold = True

    p_fdd = doc.add_paragraph(
        "Biểu đồ phân cấp chức năng (FDD) phân rã toàn bộ kiến trúc của hệ thống từ mục tiêu cấp cao "
        "thành 5 Phân hệ chính (Cấp 1) và 19 Nhóm chức năng cụ thể (Cấp 2):"
    )
    p_fdd.paragraph_format.space_after = Pt(10)

    # Insert FDD Picture
    if fdd_png.exists():
        p_img_fdd = doc.add_paragraph()
        p_img_fdd.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img_fdd.paragraph_format.space_before = Pt(6)
        p_img_fdd.paragraph_format.space_after = Pt(4)
        run_img_fdd = p_img_fdd.add_run()
        run_img_fdd.add_picture(str(fdd_png), width=Inches(6.4))

        p_cap_fdd = doc.add_paragraph()
        p_cap_fdd.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap_fdd.paragraph_format.space_after = Pt(14)
        r_cap_fdd = p_cap_fdd.add_run("Hình 1: Biểu đồ Phân cấp Chức năng (FDD) của Hệ thống Dịch thuật Đa phương thức")
        r_cap_fdd.font.size = Pt(9.5)
        r_cap_fdd.font.italic = True
        r_cap_fdd.font.color.rgb = RGBColor(71, 85, 105)

    # Descriptive text for 5 subsystems
    fdd_descriptions = [
        ("Phân hệ 1.0 - Quản trị & Điều phối Hệ thống:",
         "Khởi tạo nạp tệp cấu hình YAML/CLI, bộ điều khiển bộ nhớ MemoryController đo VRAM qua NVML để tránh lỗi OOM, bộ nhớ đệm thuật ngữ LRU Cache, và Orchestrator đồng bộ vòng lặp xử lý đa luồng."),
        ("Phân hệ 2.0 - Dịch thuật Trực quan Màn hình:",
         "Chụp màn hình (Wayland grim / MSS), phát hiện chuyển động cuộn trang (Clear-on-Scroll xóa lớp phủ ở ngưỡng chênh lệch 3.5%), nhận diện ký tự quang học RapidOCR (DBNet & CRNN), lọc bỏ rác OCR, ghép dòng thành câu hoàn chỉnh và hòa sắc lấy màu nền tiệp ảnh gốc."),
        ("Phân hệ 3.0 - Dịch thuật Âm thanh Thời gian thực:",
         "Thu nhận âm thanh Microphone hoặc Desktop Loopback, lọc khoảng lặng giọng nói bằng Silero/WebRTC VAD, nhận dạng giọng nói tự động Faster-Whisper ASR, và quản lý phụ đề viên nang 2 dòng lưu giữ câu trước."),
        ("Phân hệ 4.0 - Động cơ Dịch thuật Đa ngôn ngữ:",
         "Thực thi nhân suy luận dịch máy GPU CTranslate2 song song (Batch Parallel Pass <40ms), cổng dịch đám mây dự phòng (Cloud Fallback API) và cơ chế nạp từ điển thuật ngữ người dùng."),
        ("Phân hệ 5.0 - Giao diện & Lớp phủ Xuyên thấu:",
         "Cửa sổ trong suốt 60 FPS click-through bằng PyQt6, thuật toán giải quyết va chạm (Collision Resolver) chống phụ đề đè lên chữ trên màn hình, thanh điều khiển nổi Mini Floating Toolbar và hệ thống phím tắt nhanh.")
    ]

    for title, desc in fdd_descriptions:
        p_item = doc.add_paragraph()
        p_item.paragraph_format.left_indent = Inches(0.2)
        p_item.paragraph_format.space_after = Pt(5)
        run_bold = p_item.add_run(f"• {title} ")
        run_bold.font.bold = True
        run_bold.font.color.rgb = RGBColor(30, 58, 138)
        p_item.add_run(desc)

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # =========================================================================
    # PHẦN 3: SƠ ĐỒ USE CASE TỔNG QUÁT
    # =========================================================================
    h3 = doc.add_heading(level=1)
    r3 = h3.add_run("3. Sơ Đồ Use Case Tổng Quát (General Use Case Diagram)")
    r3.font.color.rgb = RGBColor(30, 58, 138)
    r3.font.bold = True

    p_uc = doc.add_paragraph(
        "Sơ đồ Use Case tổng quát mô tả các chức năng nghiệp vụ mà người dùng và các tác nhân hệ thống "
        "thực hiện, cùng mối quan hệ phụ thuộc gồm quan hệ bao hàm (<<include>>) và quan hệ mở rộng (<<extend>>):"
    )
    p_uc.paragraph_format.space_after = Pt(10)

    # Insert Use Case Picture
    if usecase_png.exists():
        p_img_uc = doc.add_paragraph()
        p_img_uc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img_uc.paragraph_format.space_before = Pt(6)
        p_img_uc.paragraph_format.space_after = Pt(4)
        run_img_uc = p_img_uc.add_run()
        run_img_uc.add_picture(str(usecase_png), width=Inches(6.4))

        p_cap_uc = doc.add_paragraph()
        p_cap_uc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap_uc.paragraph_format.space_after = Pt(14)
        r_cap_uc = p_cap_uc.add_run("Hình 2: Sơ đồ Use Case Tổng quát (General Use Case Diagram)")
        r_cap_uc.font.size = Pt(9.5)
        r_cap_uc.font.italic = True
        r_cap_uc.font.color.rgb = RGBColor(71, 85, 105)

    # Relationship explanation
    p_rel_title = doc.add_paragraph()
    p_rel_title.paragraph_format.space_before = Pt(6)
    p_rel_title.paragraph_format.space_after = Pt(4)
    r_rel_title = p_rel_title.add_run("Các Mối Quan Hệ Nghiệp Vụ Chính:")
    r_rel_title.font.bold = True
    r_rel_title.font.color.rgb = RGBColor(30, 58, 138)

    uc_relationships = [
        ("Quan hệ <<include>> trong UC-01 (Dịch màn hình tại chỗ):",
         "Bắt buộc bao gồm các bước: Chụp khung hình -> Nhận diện OCR & lọc rác -> Ghép dòng câu -> Dịch GPU song song -> Hòa sắc & co giãn font gốc -> Vẽ đè chữ tiếng Việt."),
        ("Quan hệ <<include>> trong UC-03 (Dịch phụ đề âm thanh trực tiếp):",
         "Bắt buộc bao gồm: Thu âm Mic/Loopback -> Lọc VAD -> Nhận dạng giọng nói Whisper ASR -> Dịch câu -> Hiển thị phụ đề viên nang 2 dòng có thuật toán chống va chạm (Collision Avoidance)."),
        ("Quan hệ <<extend>> của UC-02 (Clear-on-Scroll):",
         "Mở rộng từ luồng dịch màn hình: Khi phát hiện lăn chuột cuộn trang (diff >= 3.5%), lập tức kích hoạt xóa sạch 100% overlay cũ trong 1ms và đợi dừng cuộn 0.55s mới chụp trang mới."),
        ("Quan hệ <<extend>> của UC-04 (Snapshot F9) và UC-05 (Chọn vùng ROI):",
         "Cho phép người dùng chủ động can thiệp bằng phím tắt hoặc thanh điều khiển để chụp tức thời hoặc giới hạn không gian xử lý vào khung chữ tiểu thuyết, loại trừ thanh cuộn và quảng cáo."),
        ("Quan hệ <<extend>> của Dịch đám mây dự phòng (Cloud Fallback):",
         "Được kích hoạt khi mô hình AI GPU nội bộ không khả dụng hoặc khi người dùng cấu hình ưu tiên cổng API bên ngoài.")
    ]

    for title, desc in uc_relationships:
        p_rel = doc.add_paragraph()
        p_rel.paragraph_format.left_indent = Inches(0.2)
        p_rel.paragraph_format.space_after = Pt(4)
        run_bold = p_rel.add_run(f"• {title} ")
        run_bold.font.bold = True
        p_rel.add_run(desc)

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # =========================================================================
    # PHẦN 4: BẢNG ĐẶC TẢ TÓM TẮT CÁC USE CASE CỐT LÕI
    # =========================================================================
    h4 = doc.add_heading(level=1)
    r4 = h4.add_run("4. Bảng Đặc Tả Tóm Tắt Các Use Case Cốt Lõi")
    r4.font.color.rgb = RGBColor(30, 58, 138)
    r4.font.bold = True

    p_spec_intro = doc.add_paragraph(
        "Bảng tổng hợp đặc tả chi tiết 7 Use Case nghiệp vụ quan trọng nhất của hệ thống:"
    )
    p_spec_intro.paragraph_format.space_after = Pt(10)

    spec_table = doc.add_table(rows=8, cols=6)
    spec_headers = ["Mã UC", "Tên Use Case", "Tác nhân", "Tiền điều kiện", "Luồng sự kiện chính (Main Flow)", "Hậu điều kiện"]
    for c_idx, title in enumerate(spec_headers):
        spec_table.rows[0].cells[c_idx].paragraphs[0].text = title

    spec_data = [
        ("UC-01", "Dịch màn hình tại chỗ", "Người dùng, OS Display, GPU",
         "Ứng dụng chạy chế độ Visual, màn hình có văn bản.",
         "1. Chụp khung hình tĩnh (hoặc vùng ROI).\n2. OCR quét chữ, tự động loại bỏ rác chữ ma.\n3. Ghép dòng thành câu hoàn chỉnh.\n4. Dịch GPU song song <40ms.\n5. Lấy mẫu màu nền, ước lượng font gốc và vẽ đè chữ tiếng Việt.",
         "Lớp dịch tiếng Việt hiển thị tiệp màu nền, ngay ngắn vừa khít."),

        ("UC-02", "Xóa sạch khi cuộn trang (Clear-on-Scroll)", "Hệ thống, Người dùng",
         "Đang có lớp phủ bản dịch trên màn hình.",
         "1. Phát hiện người dùng lăn chuột (diff >= 3.5%).\n2. Xóa sạch 100% lớp phủ trong 1ms.\n3. Dừng OCR trong lúc đang cuộn.\n4. Đợi dừng cuộn đủ 0.55s mới chụp frame sạch mới để dịch.",
         "Tránh hoàn toàn hiện tượng chữ ma quái đè nhau khi đọc web novel."),

        ("UC-03", "Dịch phụ đề âm thanh trực tiếp", "Người dùng, OS Audio, GPU",
         "Chế độ Live Audio bật, có tiếng nói phát ra.",
         "1. Thu âm qua loopback hệ thống hoặc mic.\n2. VAD lọc đoạn có tiếng người nói.\n3. Faster-Whisper chuyển hóa thành tiếng Anh.\n4. Dịch sang tiếng Việt.\n5. Hiển thị viên nang nổi 2 dòng, tự tránh vị trí va chạm với ô chữ OCR.",
         "Phụ đề hiển thị mượt mà, lưu lại câu trước để người dùng kịp đọc."),

        ("UC-04", "Chụp & Dịch tức thì (Snapshot F9)", "Người dùng",
         "Người dùng muốn dịch ngay trang hiện tại.",
         "1. Người dùng bấm phím F9 hoặc nút [⚡ Dịch Trang Này].\n2. Xóa lớp phủ cũ -> nghỉ 60ms xóa đệm framebuffer -> chụp frame sạch 100% -> dịch và hiển thị ngay.",
         "Bản dịch trang mới cập nhật tức thì, tuyệt đối sạch sẽ."),

        ("UC-05", "Kéo chọn vùng quét (ROI)", "Người dùng, OS Display",
         "Người dùng muốn thu hẹp phạm vi quét.",
         "1. Bấm phím R hoặc nút [🎯 Chọn Vùng].\n2. Công cụ slurp kích hoạt cho kéo chuột chọn khung chữ.\n3. Cập nhật tọa độ ROI mới và dịch ngay vùng đó.",
         "Chỉ nội dung trong khung chữ được dịch, loại bỏ lề web và quảng cáo."),

        ("UC-06", "Ẩn / Hiện lớp dịch (Toggle Visibility)", "Người dùng",
         "Đang có bản dịch hiển thị.",
         "1. Bấm phím Esc hoặc nút [👁️ Ẩn/Hiện].\n2. Lớp phủ ẩn tức thì để đối chiếu chữ gốc.\n3. Bấm lại để hiện lại bản dịch.",
         "Người dùng dễ dàng đối chiếu văn bản gốc."),

        ("UC-07", "Giám sát VRAM & Chống tràn bộ nhớ", "GPU Driver, Hệ thống",
         "GPU đang hoạt động suy luận AI.",
         "1. MemoryController liên tục đo VRAM qua NVML.\n2. Duy trì VRAM dưới ngưỡng trần an toàn.\n3. Tự dọn dẹp hoặc offload mô hình khi chạm ngưỡng cảnh báo.",
         "Hệ thống vận hành bền bỉ 24/7, tuyệt đối không bị crash do lỗi OOM.")
    ]

    for r_idx, row_data in enumerate(spec_data, start=1):
        for c_idx, val in enumerate(row_data):
            spec_table.rows[r_idx].cells[c_idx].paragraphs[0].text = val

    spec_col_widths = [Inches(0.6), Inches(1.3), Inches(1.1), Inches(1.0), Inches(1.9), Inches(1.1)]
    for row in spec_table.rows:
        for idx, width in enumerate(spec_col_widths):
            row.cells[idx].width = width

    format_table(spec_table, header_bg="1E3A8A")

    # Footer note
    p_foot = doc.add_paragraph()
    p_foot.paragraph_format.space_before = Pt(20)
    p_foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_foot = p_foot.add_run("--- HẾT TÀI LIỆU ---")
    r_foot.font.bold = True
    r_foot.font.size = Pt(9.5)
    r_foot.font.color.rgb = RGBColor(148, 163, 184)

    doc.save(str(DOCX_PATH))
    print(f"✅ Đã tạo thành công file Word tại: {DOCX_PATH}")


if __name__ == "__main__":
    print("🚀 Bắt đầu quá trình tạo sơ đồ và xuất file DOCX...")
    fdd_path = generate_fdd_image()
    print(f"  • Đã xuất ảnh FDD: {fdd_path}")
    uc_path = generate_usecase_image()
    print(f"  • Đã xuất ảnh Use Case: {uc_path}")
    build_docx_document(fdd_path, uc_path)
