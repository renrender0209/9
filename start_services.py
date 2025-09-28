#!/usr/bin/env python3
import subprocess
import time
import os
import signal
import sys

def start_node_service():
    """Node.jsサービスを起動"""
    print("Node.jsサービスを起動中...")
    node_process = subprocess.Popen(
        ['node', 'ytdl_node_service.js'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return node_process

def start_flask_service():
    """Flaskサービスを起動"""
    print("Flaskサービスを起動中...")
    flask_process = subprocess.Popen(
        ['gunicorn', '--bind', '0.0.0.0:5000', '--reuse-port', '--reload', 'main:app'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return flask_process

def signal_handler(sig, frame):
    """シグナルハンドラー"""
    print('\nサービスを停止しています...')
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    # Node.jsサービスを起動
    node_proc = start_node_service()
    time.sleep(2)  # Node.jsサービスの起動を待つ
    
    # Flaskサービスを起動
    flask_proc = start_flask_service()
    
    try:
        # 両方のプロセスを監視
        while True:
            # Node.jsプロセスの状態確認
            if node_proc.poll() is not None:
                print("Node.jsサービスが停止しました。再起動中...")
                node_proc = start_node_service()
            
            # Flaskプロセスの状態確認
            if flask_proc.poll() is not None:
                print("Flaskサービスが停止しました。再起動中...")
                flask_proc = start_flask_service()
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nサービスを停止しています...")
        node_proc.terminate()
        flask_proc.terminate()
        node_proc.wait()
        flask_proc.wait()