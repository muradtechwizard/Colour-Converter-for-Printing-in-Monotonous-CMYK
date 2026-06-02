import sys
import os
import tempfile
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QTextEdit, 
                             QProgressBar, QLabel, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from PIL import Image, ImageOps, ImageEnhance
import pdf2image
import img2pdf

class ImageProcessor:
    """Handles intelligent duotone image processing with 100% layout preservation."""
    NAVY_BLUE = "#000080"
    WHITE = "#FFFFFF"

    @staticmethod
    def process_image(image_path: str, output_path: str) -> bool:
        try:
            # Open and ensure RGB mode
            img = Image.open(image_path).convert("RGB")
            
            # 1. Convert to grayscale to isolate luminance (brightness)
            gray_img = img.convert("L")
            
            # 2. Map luminance to Blue-White duotone. 
            # Dark pixels (text, lines) become Navy Blue. Light pixels become White.
            # Anti-aliased edges become smooth blue gradients, preserving perfect font shapes.
            duotone_img = ImageOps.colorize(gray_img, black=ImageProcessor.NAVY_BLUE, white=ImageProcessor.WHITE)
            
            # 3. Slight contrast enhancement to ensure text remains crisp and highly legible
            enhancer = ImageEnhance.Contrast(duotone_img)
            duotone_img = enhancer.enhance(1.15)
            
            duotone_img.save(output_path, optimize=True)
            return True
        except Exception as e:
            print(f"Image processing error: {e}")
            return False


class DocumentProcessor:
    """Routes and processes different document formats without destructive OCR."""
    
    @staticmethod
    def process_file(input_path: str, output_dir: str, log_callback) -> bool:
        path = Path(input_path)
        ext = path.suffix.lower()
        output_name = path.stem + "_bluewhite" + ext
        
        # Handle Images directly
        if ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif']:
            out_path = os.path.join(output_dir, output_name)
            return ImageProcessor.process_image(input_path, out_path)

        # Handle DOCX by converting to PDF first (preserves complex layouts/math)
        if ext == '.docx':
            try:
                from docx2pdf import convert
                temp_pdf = os.path.join(tempfile.gettempdir(), path.stem + "_temp.pdf")
                log_callback("Converting DOCX to PDF for layout preservation...")
                convert(input_path, temp_pdf)
                input_path = temp_pdf
                ext = '.pdf'
                output_name = path.stem + "_bluewhite.pdf"
            except Exception as e:
                log_callback(f"DOCX conversion failed (Is MS Word installed?): {e}")
                return False

        # Handle PDF
        if ext == '.pdf':
            try:
                log_callback("Rendering PDF pages to high-resolution images (300 DPI)...")
                # 300 DPI ensures crisp text, math equations, and diagrams
                images = pdf2image.convert_from_path(input_path, dpi=300)
                temp_img_dir = tempfile.mkdtemp()
                processed_imgs = []

                for i, img in enumerate(images):
                    log_callback(f"Processing page {i+1}/{len(images)}...")
                    
                    # Apply the robust duotone mapping to each page
                    gray_img = img.convert("L")
                    duotone_img = ImageOps.colorize(gray_img, black=ImageProcessor.NAVY_BLUE, white=ImageProcessor.WHITE)
                    
                    # Enhance contrast for crispness
                    enhancer = ImageEnhance.Contrast(duotone_img)
                    duotone_img = enhancer.enhance(1.15)
                    
                    out_img_path = os.path.join(temp_img_dir, f"processed_{i}.png")
                    duotone_img.save(out_img_path, "PNG", optimize=True)
                    processed_imgs.append(out_img_path)

                log_callback("Recompiling into Blue & White PDF...")
                final_pdf_path = os.path.join(output_dir, output_name)
                with open(final_pdf_path, "wb") as f:
                    f.write(img2pdf.convert(processed_imgs))
                
                # Cleanup temp files
                shutil.rmtree(temp_img_dir)
                if path.stem + "_temp.pdf" == os.path.basename(input_path):
                    os.remove(input_path) # Clean up temp DOCX pdf
                    
                return True
                
            except Exception as e:
                log_callback(f"PDF processing error: {e}")
                return False
        
        log_callback(f"Unsupported file format: {ext}")
        return False


class WorkerThread(QThread):
    """Background thread to keep GUI responsive during heavy processing."""
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, file_paths, output_dir):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir

    def run(self):
        total = len(self.file_paths)
        success_count = 0
        
        for i, file_path in enumerate(self.file_paths):
            self.log.emit(f"Starting: {Path(file_path).name}")
            
            def nested_log(msg):
                self.log.emit(f"  -> {msg}")
                
            if DocumentProcessor.process_file(file_path, self.output_dir, nested_log):
                success_count += 1
                self.log.emit(f"✅ Success: {Path(file_path).name}")
            else:
                self.log.emit(f"❌ Failed: {Path(file_path).name}")
                
            progress_pct = int(((i + 1) / total) * 100)
            self.progress.emit(progress_pct)
            
        self.finished.emit(success_count == total)


class DropZoneWidget(QFrame):
    """Custom widget that accepts drag-and-drop events."""
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #000080;
                border-radius: 10px;
                background-color: #F0F4FF;
            }
            QFrame:hover {
                background-color: #E0E8FF;
            }
        """)
        layout = QVBoxLayout(self)
        label = QLabel("📁 Drag & Drop Files or Folders Here\n(PDF, DOCX, PNG, JPG, TIFF)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #000080; font-size: 14px; font-weight: bold;")
        layout.addWidget(label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for filename in filenames:
                        if filename.lower().endswith(('.pdf', '.docx', '.png', '.jpg', '.jpeg', '.tiff', '.tif')):
                            files.append(os.path.join(root, filename))
        
        if files:
            self.files_dropped.emit(files)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blue & White Document Converter")
        self.resize(700, 600)
        self.selected_files = []
        self.output_dir = os.path.expanduser("~/Desktop/Converted_BlueWhite")
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        header = QLabel("Blue & White Theme Converter")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #000080;")
        main_layout.addWidget(header)

        self.drop_zone = DropZoneWidget()
        self.drop_zone.files_dropped.connect(self.add_files)
        main_layout.addWidget(self.drop_zone, stretch=2)

        self.file_count_label = QLabel("No files selected.")
        self.file_count_label.setStyleSheet("color: #555; font-size: 12px;")
        main_layout.addWidget(self.file_count_label)

        btn_layout = QHBoxLayout()
        
        self.btn_select = QPushButton("📂 Select Files")
        self.btn_select.clicked.connect(self.select_files)
        self.btn_select.setStyleSheet(self.btn_style())
        
        self.btn_export_dir = QPushButton("📁 Change Export Folder")
        self.btn_export_dir.clicked.connect(self.select_export_dir)
        self.btn_export_dir.setStyleSheet(self.btn_style())
        
        self.btn_convert = QPushButton("🚀 Start Conversion")
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_convert.setStyleSheet(self.btn_style("#000080", "#FFFFFF"))
        self.btn_convert.setEnabled(False)
        
        btn_layout.addWidget(self.btn_select)
        btn_layout.addWidget(self.btn_export_dir)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_convert)
        main_layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #000080; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background-color: #000080; }
        """)
        main_layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #FAFAFA; border: 1px solid #CCC; border-radius: 5px; font-family: monospace; font-size: 12px;")
        main_layout.addWidget(self.log_output, stretch=3)

    def btn_style(self, bg="#FFFFFF", text="#000080"):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: 1px solid #000080;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #E0E8FF; }}
            QPushButton:disabled {{
                background-color: #E0E0E0;
                color: #888;
                border: 1px solid #CCC;
            }}
        """

    def add_files(self, files):
        self.selected_files = list(set(self.selected_files + files))
        self.update_file_label()

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", 
            "Supported Files (*.pdf *.docx *.png *.jpg *.jpeg *.tiff *.tif);;All Files (*)"
        )
        if files:
            self.add_files(files)

    def select_export_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Export Folder", self.output_dir)
        if directory:
            self.output_dir = directory
            self.log_output.append(f"📁 Export folder set to: {self.output_dir}")

    def update_file_label(self):
        count = len(self.selected_files)
        if count > 0:
            self.file_count_label.setText(f"{count} file(s) ready for conversion.")
            self.btn_convert.setEnabled(True)
        else:
            self.file_count_label.setText("No files selected.")
            self.btn_convert.setEnabled(False)

    def log(self, message):
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def start_conversion(self):
        if not self.selected_files:
            return
        
        os.makedirs(self.output_dir, exist_ok=True)
        self.btn_convert.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_output.clear()
        self.log("🚀 Starting conversion process...")
        self.log(f"📁 Output directory: {self.output_dir}")

        self.worker = WorkerThread(self.selected_files, self.output_dir)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.start()

    def conversion_finished(self, success):
        self.btn_convert.setEnabled(True)
        if success:
            self.log("🎉 All files processed successfully!")
        else:
            self.log("⚠️ Processing completed with some errors. Check log above.")
        
        os.system(f'open "{self.output_dir}"')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
