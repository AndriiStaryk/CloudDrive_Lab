import pytest
import tempfile
import shutil
from pathlib import Path
from file_manager import FileManager

class TestFileManager:
    
    def setup_method(self):
        """Налаштування для кожного тесту"""
        self.test_dir = tempfile.mkdtemp()
        self.file_manager = FileManager(self.test_dir)
        self.test_user = "test_user"
    
    def teardown_method(self):
        """Очищення після кожного тесту"""
        shutil.rmtree(self.test_dir)
    
    def test_save_and_read_file(self):
        """Тест збереження та читання файлу"""
        content = b"Hello, World!"
        filename = "test.txt"
        
        # Зберігаємо файл
        assert self.file_manager.save_file(self.test_user, content, filename) is True
        
        # Читаємо файл
        read_content = self.file_manager.get_file_content(self.test_user, filename)
        assert read_content == content
    
    def test_delete_file(self):
        """Тест видалення файлу"""
        content = b"Test content"
        filename = "test_delete.txt"
        
        # Спочатку створюємо файл
        self.file_manager.save_file(self.test_user, content, filename)
        
        # Перевіряємо, що файл існує
        assert self.file_manager.get_file_content(self.test_user, filename) is not None
        
        # Видаляємо файл
        assert self.file_manager.delete_file(self.test_user, filename) is True
        
        # Перевіряємо, що файл видалено
        assert self.file_manager.get_file_content(self.test_user, filename) is None
    
    def test_sort_by_uploader(self):
        """Тест сортування за ім'ям того, хто завантажив (індивідуальна операція згідно варіанту)"""
        # Створюємо файли для різних користувачів
        users = ["alice", "bob", "charlie"]
        
        for user in users:
            content = f"Content by {user}".encode()
            filename = f"{user}_file.txt"
            self.file_manager.save_file(user, content, filename)
        
        # Отримуємо всі файли для кожного користувача та перевіряємо сортування
        for user in users:
            files = self.file_manager.list_files(user)
            assert len(files) == 1
            assert files[0]['uploaded_by'] == user
        
        # Перевірка що файли можна відсортувати за uploaded_by
        all_files = []
        for user in users:
            all_files.extend(self.file_manager.list_files(user))
        
        # Сортування за зростанням
        sorted_asc = sorted(all_files, key=lambda x: x['uploaded_by'])
        assert sorted_asc[0]['uploaded_by'] == "alice"
        assert sorted_asc[-1]['uploaded_by'] == "charlie"
        
        # Сортування за спаданням
        sorted_desc = sorted(all_files, key=lambda x: x['uploaded_by'], reverse=True)
        assert sorted_desc[0]['uploaded_by'] == "charlie"
        assert sorted_desc[-1]['uploaded_by'] == "alice"