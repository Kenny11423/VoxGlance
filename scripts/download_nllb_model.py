#!/usr/bin/env python3
"""Script to download and verify the NLLB-200 / Opus-MT CTranslate2 models for offline translation."""

import os
import sys
from loguru import logger


def setup_nllb_model():
    """Download pre-quantized CTranslate2 model for ultra-fast offline translation."""
    try:
        from huggingface_hub import snapshot_download
        logger.info("Checking and downloading offline CTranslate2 translation model...")
        
        # Default local model: Opus-MT en-vi CTranslate2 (lightweight ~150MB)
        local_path = snapshot_download(
            repo_id="gaudi/opus-mt-en-vi-ctranslate2",
            local_dir_use_symlinks=False,
        )
        logger.info(f"Model ready at: {local_path}")
        
        # Test loading
        import ctranslate2
        translator = ctranslate2.Translator(local_path, device="cpu")
        logger.info("Successfully loaded translation model engine.")
        return True
    except Exception as e:
        logger.error(f"Error downloading or verifying model: {e}")
        return False


if __name__ == "__main__":
    success = setup_nllb_model()
    sys.exit(0 if success else 1)
