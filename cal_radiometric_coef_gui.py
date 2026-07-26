import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.simpledialog
import numpy as np
import pandas as pd

# ======================== 核心函数 ========================
def read_means_from_csv(file_path):
    """从CSV文件中读取名为 Mean_Value 的列，返回list"""
    df = pd.read_csv(file_path)
    if 'Mean_Value' not in df.columns:
        raise ValueError(f"文件 {file_path} 中不存在列 'Mean_Value'")
    return df['Mean_Value'].astype(float).tolist()

def calculate_multi_point_coeffs_from_means(dark_mean, light_means_list, L_values):
    """利用各亮度下像元均值（1×N）计算两点校正系数，返回 G, O"""
    all_means = np.vstack([dark_mean] + light_means_list)  # (M+1, N)
    L = np.asarray(L_values, dtype=np.float64)
    L_mean = np.mean(L)

    L_centered = L - L_mean
    mean_centered = all_means - np.mean(all_means, axis=0)

    numerator = np.sum(L_centered[:, np.newaxis] * mean_centered, axis=0)
    denominator = np.sum(L_centered ** 2)
    a = numerator / denominator

    mean_y = np.mean(all_means, axis=0)
    b = mean_y - a * L_mean

    valid = a > 1e-9
    if not np.any(valid):
        raise ValueError("所有像元斜率均接近0，无法计算参考直线。")

    A_ref = np.mean(a[valid])
    B_ref = np.mean(b[valid])

    G = np.ones_like(a)
    O = np.zeros_like(b)
    G[valid] = A_ref / a[valid]
    O[valid] = B_ref - G[valid] * b[valid]
    O[~valid] = B_ref

    return G, O

# ======================== GUI 应用程序类 ========================
class RadiometricCalibrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("相对辐射定标系数计算器")
        self.root.geometry("800x550")

        # 存储文件数据：每行 {'path': str, 'L': float, 'item_id': str}
        self.file_records = []

        self.create_widgets()

    def create_widgets(self):
        # 说明标签
        ttk.Label(self.root, text="添加定标数据文件（CSV，含Mean_Value列），并指定每个文件的辐射亮度（暗场设为0）",
                  padding=5).pack(anchor=tk.W, padx=10, pady=5)

        # 文件表格区域
        frame_table = ttk.Frame(self.root)
        frame_table.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("文件路径", "辐射亮度")
        self.tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=10)
        self.tree.heading("文件路径", text="文件路径")
        self.tree.heading("辐射亮度", text="辐射亮度")
        self.tree.column("文件路径", width=550)
        self.tree.column("辐射亮度", width=100, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame_table, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 双击辐射亮度单元格可编辑
        self.tree.bind("<Double-1>", self.on_double_click)

        # 按钮区
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="添加文件（可多选）", command=self.add_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除选中文件", command=self.remove_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="修改选中辐亮度", command=self.edit_radiance).pack(side=tk.LEFT, padx=5)

        # 计算/保存区
        calc_frame = ttk.Frame(self.root)
        calc_frame.pack(fill=tk.X, padx=10, pady=5)

        self.btn_calc = ttk.Button(calc_frame, text="计算定标系数", command=self.calculate)
        self.btn_calc.pack(side=tk.LEFT, padx=5)

        self.btn_save = ttk.Button(calc_frame, text="保存系数...", state=tk.DISABLED, command=self.save_coeffs)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        ttk.Button(calc_frame, text="退出", command=self.root.destroy).pack(side=tk.RIGHT, padx=5)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 存储计算结果
        self.G = None
        self.O = None

    def add_files(self):
        """打开多选文件对话框，添加文件到列表，默认辐亮度为0"""
        filenames = filedialog.askopenfilenames(
            title="选择定标数据CSV文件（可多选）",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        for f in filenames:
            # 避免重复添加相同路径
            if any(rec['path'] == f for rec in self.file_records):
                continue
            item_id = self.tree.insert("", tk.END, values=(f, "0.0"))
            self.file_records.append({'path': f, 'L': 0.0, 'item_id': item_id})
        if filenames:
            self.status_var.set(f"已添加 {len(filenames)} 个文件")
        else:
            self.status_var.set("未选择文件")

    def remove_files(self):
        """删除选中的文件"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("未选择", "请先选择要删除的文件。")
            return
        for item in selected:
            self.tree.delete(item)
            self.file_records = [rec for rec in self.file_records if rec['item_id'] != item]
        self.status_var.set(f"已删除 {len(selected)} 个文件")

    def on_double_click(self, event):
        """双击辐射亮度单元格弹出编辑框"""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if column == "#2":  # 第二列（辐射亮度）
            self._edit_cell(item)

    def edit_radiance(self):
        """通过按钮修改选中行的辐亮度"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("未选择", "请先选择要修改的文件。")
            return
        if len(selected) > 1:
            messagebox.showwarning("多选", "一次只能修改一个文件的辐亮度。")
            return
        self._edit_cell(selected[0])

    def _edit_cell(self, item_id):
        """弹窗输入新的辐亮度值"""
        # 查找记录
        rec = next((r for r in self.file_records if r['item_id'] == item_id), None)
        if not rec:
            return
        new_val = tk.simpledialog.askfloat(
            "修改辐射亮度",
            f"文件:\n{os.path.basename(rec['path'])}\n当前值: {rec['L']}\n请输入新的辐射亮度：",
            initialvalue=rec['L']
        )
        if new_val is not None:
            rec['L'] = new_val
            self.tree.set(item_id, "辐射亮度", f"{new_val:.4f}")

    def calculate(self):
        """从表格收集数据，分离暗场与亮场，计算系数"""
        if not self.file_records:
            messagebox.showerror("无数据", "请先添加定标数据文件。")
            return

        # 构建按辐亮度排序的列表
        records = sorted(self.file_records, key=lambda x: x['L'])
        # 分离暗场（L=0）文件
        dark_recs = [r for r in records if r['L'] == 0.0]
        if not dark_recs:
            messagebox.showerror("缺少暗场", "至少需要一个辐射亮度为 0 的文件作为暗场。")
            return
        # 如果有多个暗场，取第一个，其余忽略或可提示
        if len(dark_recs) > 1:
            messagebox.showwarning("多个暗场", "检测到多个辐射亮度为0的文件，将只使用第一个作为暗场，其余将被忽略。")
        dark_rec = dark_recs[0]

        # 亮场文件（L ≠ 0）
        light_recs = [r for r in records if r['L'] != 0.0]
        if not light_recs:
            messagebox.showerror("缺少亮场", "至少需要一个辐射亮度不为0的亮场文件。")
            return

        # 检查亮度值是否唯一（避免除零等问题）
        L_set = set(r['L'] for r in records)
        if len(L_set) < 2:
            messagebox.showerror("亮度值不足", "所有文件的辐射亮度必须至少包含两个不同的值（含0）。")
            return

        # 读取暗场均值
        try:
            dark_mean = np.array(read_means_from_csv(dark_rec['path']))
        except Exception as e:
            messagebox.showerror("读取暗场失败", f"无法读取暗场文件：\n{dark_rec['path']}\n错误：{e}")
            return

        # 读取亮场均值，并收集亮度值
        light_means = []
        L_vals = [0.0]  # 暗场对应0
        for rec in light_recs:
            try:
                mean_arr = np.array(read_means_from_csv(rec['path']))
                light_means.append(mean_arr)
                L_vals.append(rec['L'])
            except Exception as e:
                messagebox.showerror("读取亮场失败", f"文件：\n{rec['path']}\n错误：{e}")
                return

        # 检查像元数一致性
        N = len(dark_mean)
        for i, arr in enumerate(light_means):
            if len(arr) != N:
                messagebox.showerror("尺寸不一致",
                    f"暗场像元数({N})与亮场文件\n{light_recs[i]['path']}\n的像元数({len(arr)})不一致。")
                return

        # 计算定标系数
        try:
            self.G, self.O = calculate_multi_point_coeffs_from_means(dark_mean, light_means, L_vals)
        except Exception as e:
            messagebox.showerror("计算失败", f"定标系数计算失败：{e}")
            return

        # 更新界面
        self.btn_save.config(state=tk.NORMAL)
        self.status_var.set(
            f"计算完成：{N}个像元，增益范围 [{self.G.min():.4f}, {self.G.max():.4f}]，"
            f"偏置范围 [{self.O.min():.4f}, {self.O.max():.4f}]"
        )
        messagebox.showinfo("计算成功", "定标系数计算完成，可点击“保存系数”导出。")

    def save_coeffs(self):
        """保存增益和偏置系数到CSV"""
        if self.G is None or self.O is None:
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv")],
            title="保存定标系数"
        )
        if not file_path:
            return
        try:
            df = pd.DataFrame({"Gain": self.G, "Offset": self.O})
            df.to_csv(file_path, index=False)
            self.status_var.set(f"系数已保存至 {file_path}")
            messagebox.showinfo("保存成功", f"定标系数已保存到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

# ======================== 主入口 ========================
if __name__ == "__main__":
    root = tk.Tk()
    app = RadiometricCalibrationApp(root)
    root.mainloop()