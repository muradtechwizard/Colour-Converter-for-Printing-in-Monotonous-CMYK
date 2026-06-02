# 🔵 Blue & White Document Converter

A production-ready, native macOS desktop application built with Python and PyQt6. It intelligently converts PDF, DOCX, and Image files (PNG, JPG, TIFF) into a crisp "Navy Blue & White" duotone theme. 

Perfect for saving black ink cartridges, creating stylized blue-and-white printouts, or reformatting complex math equations, documents, and diagrams without losing a single pixel of formatting.

## ✨ Features
- **100% Layout Preservation:** Uses luminance-based color mapping to ensure complex math equations, tables, and formatting remain perfectly intact (no destructive OCR).
- **Intelligent Duotone Mapping:** Dark pixels (text, lines) become Navy Blue, while light pixels become White. Anti-aliased edges are preserved for crisp, professional rendering.
- **Modern macOS GUI:** Built with PyQt6, featuring a native look, drag-and-drop support, and native macOS file/folder pickers.
- **Background Processing:** Heavy file processing runs on a separate thread, keeping the GUI completely responsive with real-time progress tracking.
- **Multi-Format Support:** 
  - **Inputs:** PDF, DOCX, PNG, JPG, JPEG, TIFF.
  - **Outputs:** PDF (for documents), Image/PDF (for images).

---

## 📋 Prerequisites
Before installing, ensure you have the following installed on your macOS system:
1. **Python 3** (Pre-installed on most modern macOS versions, or install via `brew install python`).
2. **Homebrew** (macOS package manager).
3. **Poppler** (Required for high-fidelity PDF rendering):
   ```bash
   brew install poppler

## 3. Create & Activate Virtual Environment
  ```bash
       python3 -m venv venv
source venv/bin/activate


