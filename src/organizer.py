import os
print("プログラムを開始します。現在の場所:", os.getcwd())
import sys
import shutil
import json
import logging
import hashlib
from datetime import datetime
import tkinter as tk
from tkinter import filedialog  # 追加：フォルダ選択用

class StorageManager:
    def __init__(self, config_path='config/settings.json'):
        self.load_config(config_path)
        
        # --- 追加：フォルダを画面で選択する処理 ---
        print("整理したいフォルダを選択してください...")
        root = tk.Tk()
        root.withdraw() # 余分なウィンドウを隠す
        # フォルダ選択ダイアログを表示
        selected_dir = filedialog.askdirectory(title="整理対象のフォルダを選択")
        
        if selected_dir:
            self.target_dir = selected_dir
            print(f"対象フォルダを以下に変更しました: {self.target_dir}")
        else:
            print("フォルダが選択されなかったため、設定ファイルのパスを使用します。")
        self.setup_logging()

    def load_config(self, path):
        """設定ファイルの読み込み"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.target_dir = self.config['target_directory']
            self.rules = self.config['rules']
            self.archive_format = self.config.get('archive_date_format', '%Y%m')
        except FileNotFoundError:
            print(f"Error: Config file not found at {path}")
            sys.exit(1)

    def setup_logging(self):
        """監査証跡のための詳細ログ設定"""
        # logsフォルダがなければ作成する ---
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, f"storage_op_{datetime.now().strftime('%Y%m%d')}.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            encoding='utf-8'
        )
        self.logger = logging.getLogger()

    def calculate_hash(self, filepath):
        """SHA-256を用いたファイル整合性(改ざん検知)の検証"""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Hash calculation error for {filepath}: {e}")
            return None

    def organize(self):
        """メインの整理ロジック"""
        self.logger.info("=== Operation Started ===")
        
        if not os.path.exists(self.target_dir):
            self.logger.error(f"Target directory missing: {self.target_dir}")
            return

        for filename in os.listdir(self.target_dir):
            source_path = os.path.join(self.target_dir, filename)
            
            # フォルダや隠しファイルはスキップ
            if os.path.isdir(source_path) or filename.startswith('.'):
                continue

            ext = os.path.splitext(filename)[1].lower()
            dest_folder_name = self.rules.get(ext, "Others")
            
            # 世代管理(日付フォルダ)の定義
            date_folder = datetime.now().strftime(self.archive_format)
            dest_dir = os.path.join(self.target_dir, dest_folder_name, date_folder)
            
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            # 移動前のハッシュ保存
            pre_hash = self.calculate_hash(source_path)
            dest_path = os.path.join(dest_dir, filename)
            
            try:
                # ファイル移動の実行
                shutil.move(source_path, dest_path)
                
                # 移動後の整合性検証
                post_hash = self.calculate_hash(dest_path)
                
                if pre_hash == post_hash:
                    self.logger.info(f"[SUCCESS] {filename} -> {dest_folder_name}/{date_folder} (Hash: {post_hash})")
                else:
                    self.logger.critical(f"[INTEGRITY FAILURE] Hash mismatch detected for {filename}!")
            except Exception as e:
                self.logger.error(f"[SYSTEM ERROR] Failed to move {filename}: {str(e)}")

        self.logger.info("=== Operation Completed ===")

if __name__ == '__main__':
    manager = StorageManager()
    manager.organize()