# main.py
import os
import sys

from PyQt6.QtWidgets import QApplication

# Добавляем корень проекта в путь, чтобы импорты src.* работали
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.gui.main_window import MainWindow


def main():
    # Создаем папку для вывода, если её нет
    os.makedirs("data/output", exist_ok=True)
    
    app = QApplication(sys.argv)
    
    # Опционально: темная тема для современного вида
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()