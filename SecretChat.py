import os
import sys
import socket
import threading
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QLabel, QProgressBar
)
from PyQt5.QtGui import QFont, QColor, QTextCursor
from PyQt5.QtCore import Qt

# Параметры сети
BROADCAST_PORT = 12345
BUFFER_SIZE = 1024
SAVE_DIR = "received_files"

# Создаем папку для сохраненных файлов, если ее нет
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)


class ChatApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

        # Сетевые настройки
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("", BROADCAST_PORT))
        self.running = True

        # Поток для получения сообщений
        self.receiver_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self.receiver_thread.start()

    def init_ui(self):
        self.setWindowTitle("Modern Chat App")
        self.setGeometry(100, 100, 800, 600)

        # Основные элементы интерфейса
        self.chat_display = QTextEdit(self)
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Arial", 12))
        self.chat_display.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; border: none; padding: 10px;")

        self.message_input = QLineEdit(self)
        self.message_input.setFont(QFont("Arial", 12))
        self.message_input.setPlaceholderText("Введите сообщение...")
        self.message_input.setStyleSheet("background-color: #333333; color: #ffffff; padding: 10px; border-radius: 5px;")

        self.send_button = QPushButton("Отправить", self)
        self.send_button.setFont(QFont("Arial", 12))
        self.send_button.setStyleSheet("background-color: #0078d7; color: white; padding: 10px; border-radius: 5px;")
        self.send_button.clicked.connect(self.send_message)

        self.file_button = QPushButton("Отправить файл", self)
        self.file_button.setFont(QFont("Arial", 12))
        self.file_button.setStyleSheet("background-color: #4caf50; color: white; padding: 10px; border-radius: 5px;")
        self.file_button.clicked.connect(self.send_file)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: #333333; color: white; border: none; }")

        # Верхняя панель
        self.nickname_label = QLabel("Ваш ник: ", self)
        self.nickname_label.setFont(QFont("Arial", 12))
        self.nickname_label.setStyleSheet("color: white;")
        self.nickname_input = QLineEdit(self)
        self.nickname_input.setFont(QFont("Arial", 12))
        self.nickname_input.setStyleSheet("background-color: #333333; color: #ffffff; padding: 5px; border-radius: 5px;")
        self.nickname_input.setPlaceholderText("Введите ник...")

        # Компоновка
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.nickname_label)
        top_layout.addWidget(self.nickname_input)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.message_input)
        bottom_layout.addWidget(self.send_button)
        bottom_layout.addWidget(self.file_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.chat_display)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(bottom_layout)

        central_widget = QWidget(self)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.setStyleSheet("background-color: #2e2e2e;")

    def send_message(self):
        message = self.message_input.text().strip()
        if message:
            nickname = self.nickname_input.text().strip() or "Anon"
            full_message = f"{nickname}: {message}"
            self.sock.sendto(full_message.encode(), ("<broadcast>", BROADCAST_PORT))
            self.chat_display.append(full_message)
            self.message_input.clear()

    def send_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл для отправки")
        if file_path:
            try:
                filename = os.path.basename(file_path)
                with open(file_path, "rb") as file:
                    data = file.read()

                chunk_size = 1024
                chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
                total_chunks = len(chunks)

                file_message = f"FILE:{filename}:{len(data)}:{total_chunks}"
                self.sock.sendto(file_message.encode(), ("<broadcast>", BROADCAST_PORT))

                for idx, chunk in enumerate(chunks):
                    self.sock.sendto(chunk, ("<broadcast>", BROADCAST_PORT))
                    progress = int((idx + 1) / total_chunks * 100)
                    self.progress_bar.setValue(progress)
                    self.progress_bar.setVisible(True)

                self.progress_bar.setVisible(False)
                self.chat_display.append(f"Вы отправили файл: {filename}")
            except Exception as e:
                self.chat_display.append(f"Ошибка отправки файла: {e}")

    def receive_messages(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(BUFFER_SIZE)
                message = data.decode()
                if message.startswith("FILE:"):
                    _, filename, file_size, total_chunks = message.split(":")
                    file_size = int(file_size)
                    total_chunks = int(total_chunks)

                    received_data = bytearray()
                    for _ in range(total_chunks):
                        chunk, _ = self.sock.recvfrom(BUFFER_SIZE)
                        received_data.extend(chunk)

                    with open(os.path.join(SAVE_DIR, filename), "wb") as file:
                        file.write(received_data)
                    self.chat_display.append(f"Получен файл: {filename}")
                else:
                    self.chat_display.append(message)
                    self.chat_display.moveCursor(QTextCursor.End)
            except Exception as e:
                self.chat_display.append(f"Ошибка: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client_window = ChatApp()
    client_window.show()
    sys.exit(app.exec_())
