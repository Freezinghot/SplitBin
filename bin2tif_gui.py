# -*- coding: utf-8 -*-
# @File  : bin2tif_gui.py
# @Author: Freezinghot
# @Date  : 2026/7/24
# @Desc  : BIN转TIF图像工具 - GUI版本（可直接打包）

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
import traceback
from pathlib import Path
import numpy as np
import tifffile
from tqdm import tqdm


class Bin2TifApp:
    """BIN转TIF图像工具GUI应用"""

    def __init__(self, root):
        self.root = root
        self.root.title("BIN转TIF图像工具")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        # 变量
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.status = tk.StringVar(value="就绪")
        self.is_processing = False

        # 设置UI
        self.setup_ui()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """设置UI界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="BIN转TIF图像提取工具",
                                font=('微软雅黑', 14, 'bold'))
        title_label.pack(pady=(0, 15))

        # 输入目录
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="输入目录:", font=('微软雅黑', 10)).pack(side=tk.LEFT)

        input_entry = ttk.Entry(input_frame, textvariable=self.input_dir, width=50)
        input_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)

        ttk.Button(input_frame, text="浏览...", command=self.browse_input,
                   width=10).pack(side=tk.RIGHT)

        # 输出目录
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=5)

        ttk.Label(output_frame, text="输出目录:", font=('微软雅黑', 10)).pack(side=tk.LEFT)

        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir, width=50)
        output_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)

        ttk.Button(output_frame, text="浏览...", command=self.browse_output,
                   width=10).pack(side=tk.RIGHT)

        # 信息显示框架
        info_frame = ttk.LabelFrame(main_frame, text="文件信息", padding="10")
        info_frame.pack(fill=tk.X, pady=10)

        # 文件数量信息
        self.mss_count_label = ttk.Label(info_frame, text="MSS文件数量: 0")
        self.mss_count_label.pack(anchor=tk.W, pady=2)

        self.pan_count_label = ttk.Label(info_frame, text="PAN文件数量: 0")
        self.pan_count_label.pack(anchor=tk.W, pady=2)

        self.total_count_label = ttk.Label(info_frame, text="总计文件数量: 0")
        self.total_count_label.pack(anchor=tk.W, pady=2)

        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)

        self.progress = ttk.Progressbar(progress_frame, mode='determinate',
                                        length=400, maximum=100)
        self.progress.pack(fill=tk.X, expand=True)

        # 状态标签
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)

        ttk.Label(status_frame, text="状态:", font=('微软雅黑', 10)).pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_frame, textvariable=self.status,
                                      font=('微软雅黑', 10, 'bold'))
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))

        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15)

        self.start_btn = ttk.Button(button_frame, text="开始转换",
                                    command=self.start_processing, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="停止",
                                   command=self.stop_processing, width=15,
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="清空日志",
                   command=self.clear_log, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="退出",
                   command=self.on_closing, width=15).pack(side=tk.LEFT, padx=5)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15,
                                                  wrap=tk.WORD,
                                                  font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志颜色标签
        self.log_text.tag_config('info', foreground='blue')
        self.log_text.tag_config('success', foreground='green')
        self.log_text.tag_config('error', foreground='red')
        self.log_text.tag_config('warning', foreground='orange')

        # 初始日志
        self.log("程序已启动，请选择输入和输出目录", 'info')

    def browse_input(self):
        """浏览输入目录"""
        directory = filedialog.askdirectory(title="选择输入目录")
        if directory:
            self.input_dir.set(directory)
            self.log(f"选择输入目录: {directory}", 'info')
            # 自动扫描文件
            self.scan_files()

    def browse_output(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
            self.log(f"选择输出目录: {directory}", 'info')

            # 检查输出目录是否可写
            try:
                test_file = Path(directory) / "test_write.tmp"
                test_file.touch()
                test_file.unlink()
                self.log("输出目录可写", 'success')
            except Exception as e:
                self.log(f"输出目录不可写: {e}", 'error')
                messagebox.showwarning("警告", f"输出目录不可写:\n{e}")

    def scan_files(self):
        """扫描输入目录中的文件"""
        input_path = self.input_dir.get()
        if not input_path:
            return

        try:
            input_dir = Path(input_path)
            if not input_dir.exists():
                self.log(f"目录不存在: {input_path}", 'error')
                return

            # 统计文件
            mss_files = []
            pan_files = []

            for file in input_dir.glob("*.bin"):
                if 'w8696_h4000' in file.name:
                    pan_files.append(file)
                elif 'w2272_h1000' in file.name:
                    mss_files.append(file)

            # 更新显示
            self.mss_count_label.config(text=f"MSS文件数量: {len(mss_files)}")
            self.pan_count_label.config(text=f"PAN文件数量: {len(pan_files)}")
            self.total_count_label.config(text=f"总计文件数量: {len(mss_files) + len(pan_files)}")

            self.log(f"扫描完成: MSS={len(mss_files)}, PAN={len(pan_files)}", 'info')

            if len(mss_files) == 0 and len(pan_files) == 0:
                self.log("未找到任何匹配的BIN文件", 'warning')

        except Exception as e:
            self.log(f"扫描文件时出错: {e}", 'error')

    def log(self, message, tag='info'):
        """添加日志"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        self.log_text.insert(tk.END, log_message, tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log("日志已清空", 'info')

    def update_progress(self, current, total):
        """更新进度条"""
        if total > 0:
            progress_value = (current / total) * 100
            self.progress['value'] = progress_value
            self.status.set(f"处理中: {current}/{total}")
            self.root.update_idletasks()

    def start_processing(self):
        """开始处理"""
        # 验证输入
        if not self.input_dir.get():
            messagebox.showerror("错误", "请选择输入目录")
            return

        if not self.output_dir.get():
            messagebox.showerror("错误", "请选择输出目录")
            return

        # 检查输入目录是否存在
        if not Path(self.input_dir.get()).exists():
            messagebox.showerror("错误", "输入目录不存在")
            return

        # 检查输出目录
        output_path = Path(self.output_dir.get())
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            # 测试写入权限
            test_file = output_path / "test_write.tmp"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            messagebox.showerror("错误", f"输出目录无法写入:\n{e}")
            return

        # 确认操作
        if not messagebox.askyesno("确认", "确定要开始转换吗？"):
            return

        # 禁用按钮，启动进度条
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.is_processing = True
        self.progress['value'] = 0
        self.status.set("正在处理...")

        self.log("=" * 60, 'info')
        self.log("开始处理", 'info')

        # 在新线程中处理
        thread = threading.Thread(target=self.process_files)
        thread.daemon = True
        thread.start()

    def stop_processing(self):
        """停止处理"""
        self.is_processing = False
        self.log("用户请求停止处理...", 'warning')
        self.status.set("正在停止...")

    def process_files(self):
        """处理文件"""
        try:
            input_dir = Path(self.input_dir.get())
            output_dir = Path(self.output_dir.get())

            # 收集文件
            mss_files = []
            pan_files = []

            for file in input_dir.glob("*.bin"):
                if 'w8696_h4000' in file.name:
                    pan_files.append(file)
                elif 'w2272_h1000' in file.name:
                    mss_files.append(file)

            total_files = len(mss_files) + len(pan_files)

            if total_files == 0:
                self.log("没有找到需要处理的文件", 'error')
                self.processing_done()
                return

            self.log(f"找到 {len(mss_files)} 个MSS文件, {len(pan_files)} 个PAN文件", 'info')

            # 处理MSS文件
            if mss_files and self.is_processing:
                self.log(f"开始处理MSS文件 ({len(mss_files)} 个)", 'info')
                self.process_mss_files(mss_files, output_dir)

            # 处理PAN文件
            if pan_files and self.is_processing:
                self.log(f"开始处理PAN文件 ({len(pan_files)} 个)", 'info')
                self.process_pan_files(pan_files, output_dir)

            # 完成
            if self.is_processing:
                self.log("所有文件处理完成！", 'success')
                messagebox.showinfo("完成", f"转换完成！\n处理了 {total_files} 个文件")
            else:
                self.log("处理已被用户停止", 'warning')

        except Exception as e:
            error_msg = traceback.format_exc()
            self.log(f"处理过程中出错:\n{error_msg}", 'error')
            messagebox.showerror("错误", f"处理失败:\n{str(e)}")
        finally:
            self.processing_done()

    def process_mss_files(self, mss_files, output_dir):
        """处理MSS文件"""
        total = len(mss_files)

        for idx, file_path in enumerate(mss_files, 1):
            if not self.is_processing:
                break

            try:
                self.log(f"处理MSS: {file_path.name}", 'info')
                self.mss_split_bin2raw(file_path, output_dir)
                self.update_progress(idx, total)
                self.log(f"完成: {file_path.name}", 'success')
            except Exception as e:
                self.log(f"处理 {file_path.name} 时出错: {e}", 'error')

    def process_pan_files(self, pan_files, output_dir):
        """处理PAN文件"""
        total = len(pan_files)

        for idx, file_path in enumerate(pan_files, 1):
            if not self.is_processing:
                break

            try:
                self.log(f"处理PAN: {file_path.name}", 'info')
                self.pan_bin2raw(file_path, output_dir)
                self.update_progress(idx, total)
                self.log(f"完成: {file_path.name}", 'success')
            except Exception as e:
                self.log(f"处理 {file_path.name} 时出错: {e}", 'error')

    def mss_split_bin2raw(self, mss_binname, output_dir):
        """MSS BIN转TIF"""
        basename = os.path.basename(mss_binname)

        # 生成输出文件名
        b1_filename = os.path.join(output_dir, 'B1_' + basename.replace('bin', 'tif'))
        b2_filename = os.path.join(output_dir, 'B2_' + basename.replace('bin', 'tif'))
        b3_filename = os.path.join(output_dir, 'B3_' + basename.replace('bin', 'tif'))
        b4_filename = os.path.join(output_dir, 'B4_' + basename.replace('bin', 'tif'))

        # 读取文件
        with open(mss_binname, 'rb') as bf:
            bf_data = bf.read()

        n = 4544
        bf_split = [bf_data[i:i + n] for i in range(0, len(bf_data), n)]
        groups = tuple([bf_split[i] for i in range(start, len(bf_split), 4)] for start in range(4))

        # 处理各组
        for bs in groups:
            if bs[0][10] == 1:
                trimmed = [d[256:-4] for d in bs]
                data_bytes = b''.join(trimmed)
                unpack_bytes = self.convert_16bit_to_12bit(data_bytes)
                tifffile.imwrite(b1_filename, unpack_bytes, photometric='minisblack')
            elif bs[0][10] == 2:
                trimmed = [d[256:-4] for d in bs]
                data_bytes = b''.join(trimmed)
                unpack_bytes = self.convert_16bit_to_12bit(data_bytes)
                tifffile.imwrite(b2_filename, unpack_bytes, photometric='minisblack')
            elif bs[0][10] == 3:
                trimmed = [d[256:-4] for d in bs]
                data_bytes = b''.join(trimmed)
                unpack_bytes = self.convert_16bit_to_12bit(data_bytes)
                tifffile.imwrite(b3_filename, unpack_bytes, photometric='minisblack')
            elif bs[0][10] == 4:
                trimmed = [d[256:-4] for d in bs]
                data_bytes = b''.join(trimmed)
                unpack_bytes = self.convert_16bit_to_12bit(data_bytes)
                tifffile.imwrite(b4_filename, unpack_bytes, photometric='minisblack')

    def pan_bin2raw(self, pan_filename, output_dir):
        """PAN BIN转TIF"""
        basename = os.path.basename(pan_filename)
        export_filename = os.path.join(output_dir, 'P_' + basename.replace('bin', 'tif'))

        with open(pan_filename, 'rb') as bf:
            bf_data = bf.read()

        n = 17392  # (8568+128) * 2
        pf_split = [bf_data[i:i + n] for i in range(0, len(bf_data), n)]

        # 处理数据
        all_data = b''
        for pf in pf_split:
            trimmed = pf[256:]
            all_data += trimmed

        unpack_bytes = self.convert_16bit_to_12bit(all_data, width=8568)
        tifffile.imwrite(export_filename, unpack_bytes, photometric='minisblack')

    def convert_16bit_to_12bit(self, data_bytes, mode='low', endian='little', width=2142):
        """
        批量转换2字节数据为12位值，返回uint16数组

        Args:
            data_bytes: bytes对象
            mode: 'low' - 数据在低12位; 'shift' - 数据左移4位
            endian: 'little' 或 'big'
            width: 图像宽度

        Returns:
            np.ndarray: uint16类型的12位值数组 (0-4095)
        """
        if len(data_bytes) % 2 != 0:
            raise ValueError("数据长度必须是2的倍数")

        # 将bytes转换为uint16数组（根据端序）
        if endian == 'little':
            dtype = np.dtype('<u2')  # 小端序 uint16
        else:
            dtype = np.dtype('>u2')  # 大端序 uint16

        # 直接转换为uint16数组
        values_16bit = np.frombuffer(data_bytes, dtype=dtype)

        # 提取12位值
        if mode == 'low':
            values_12bit = values_16bit & 0xFFF
        elif mode == 'shift':
            values_12bit = values_16bit >> 4
        else:
            raise ValueError("mode必须是 'low' 或 'shift'")

        # 重塑为二维数组
        height = len(values_12bit) // width
        return values_12bit.astype(np.uint16).reshape(height, width)

    def processing_done(self):
        """处理完成后的清理"""
        self.is_processing = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress['value'] = 100
        self.status.set("处理完成")
        self.root.update_idletasks()

    def on_closing(self):
        """窗口关闭事件"""
        if self.is_processing:
            if not messagebox.askyesno("确认退出", "正在处理中，确定要退出吗？"):
                return
            self.is_processing = False

        self.root.destroy()


# ==================== 打包启动函数 ====================

def main():
    """主函数"""
    try:
        root = tk.Tk()
        app = Bin2TifApp(root)
        root.mainloop()
    except Exception as e:
        print(f"启动程序时出错: {e}")
        traceback.print_exc()
        input("按Enter键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()