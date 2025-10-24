import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
import openslide
from PIL import Image
import threading


class SVSTilerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SVS切片工具")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        # 设置中文字体支持
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.configure("TEntry", font=("SimHei", 10))

        # 变量初始化
        self.svs_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.tile_size = tk.IntVar(value=1024)
        self.quality = tk.IntVar(value=100)
        self.processing = False

        self.create_widgets()

    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # SVS文件选择
        ttk.Label(main_frame, text="SVS文件路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.svs_path, width=50).grid(row=0, column=1, pady=5)
        ttk.Button(main_frame, text="浏览...", command=self.browse_svs).grid(row=0, column=2, padx=5, pady=5)

        # 输出文件夹选择
        ttk.Label(main_frame, text="输出文件夹:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_dir, width=50).grid(row=1, column=1, pady=5)
        ttk.Button(main_frame, text="浏览...", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)

        # 切片大小设置
        ttk.Label(main_frame, text="切片大小:").grid(row=2, column=0, sticky=tk.W, pady=5)
        size_frame = ttk.Frame(main_frame)
        size_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Entry(size_frame, textvariable=self.tile_size, width=10).pack(side=tk.LEFT)
        ttk.Label(size_frame, text="x 像素").pack(side=tk.LEFT, padx=5)

        # 质量设置（PNG格式主要用于兼容）
        ttk.Label(main_frame, text="保存质量:").grid(row=3, column=0, sticky=tk.W, pady=5)
        quality_frame = ttk.Frame(main_frame)
        quality_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        ttk.Entry(quality_frame, textvariable=self.quality, width=10).pack(side=tk.LEFT)
        ttk.Label(quality_frame, text="(1-100)").pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress_var = tk.DoubleVar()
        ttk.Label(main_frame, text="处理进度:").grid(row=4, column=0, sticky=tk.W, pady=10)
        self.progress_bar = ttk.Progressbar(
            main_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.grid(row=4, column=1, pady=10, sticky=tk.EW)

        # 状态标签
        self.status_label = ttk.Label(main_frame, text="就绪", foreground="blue")
        self.status_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=5)

        # 日志文本框
        ttk.Label(main_frame, text="处理日志:").grid(row=6, column=0, sticky=tk.NW, pady=5)
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=6, column=1, columnspan=2, sticky=tk.NSEW, pady=5)

        self.log_text = tk.Text(log_frame, height=8, width=50, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 处理按钮
        self.process_btn = ttk.Button(
            main_frame, text="开始切片", command=self.start_processing
        )
        self.process_btn.grid(row=7, column=0, columnspan=3, pady=20)

        # 配置网格权重，使控件适应窗口大小变化
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)

    def browse_svs(self):
        file_path = filedialog.askopenfilename(
            title="选择SVS文件",
            filetypes=[("SVS文件", "*.svs"), ("所有文件", "*.*")]
        )
        if file_path:
            self.svs_path.set(file_path)

    def browse_output(self):
        dir_path = filedialog.askdirectory(title="选择输出文件夹")
        if dir_path:
            self.output_dir.set(dir_path)

    def log(self, message):
        """在日志文本框中添加信息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # 滚动到最后一行
        self.log_text.config(state=tk.DISABLED)

    def update_status(self, message, color="blue"):
        """更新状态标签"""
        self.status_label.config(text=message, foreground=color)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_var.set(value)

    def start_processing(self):
        """开始处理（在新线程中执行以避免界面冻结）"""
        if self.processing:
            messagebox.showinfo("提示", "正在处理中，请等待完成")
            return

        # 验证输入
        svs_path = self.svs_path.get()
        output_dir = self.output_dir.get()
        tile_size = self.tile_size.get()
        quality = self.quality.get()

        if not svs_path or not os.path.exists(svs_path):
            messagebox.showerror("错误", "请选择有效的SVS文件")
            return

        if not output_dir:
            messagebox.showerror("错误", "请选择输出文件夹")
            return

        if tile_size <= 0:
            messagebox.showerror("错误", "切片大小必须为正数")
            return

        if quality < 1 or quality > 100:
            messagebox.showerror("错误", "质量必须在1-100之间")
            return

        # 禁用按钮，防止重复点击
        self.process_btn.config(state=tk.DISABLED)
        self.processing = True
        self.update_status("开始处理...")
        self.update_progress(0)
        self.log("===== 开始处理 =====")

        # 在新线程中执行处理函数
        threading.Thread(
            target=self.slice_svs_to_tiles_hq,
            args=(svs_path, output_dir, tile_size, quality),
            daemon=True
        ).start()

    def slice_svs_to_tiles_hq(self, svs_path, output_dir, tile_size, quality):
        """高清切片SVS文件为指定大小的小块（在后台线程执行）"""
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            self.log(f"输出目录: {output_dir}")

            # 打开SVS文件
            slide = openslide.OpenSlide(svs_path)
            width, height = slide.dimensions

            self.log(f"成功打开SVS文件: {os.path.basename(svs_path)}")
            self.log(f"原始分辨率: {width}x{height}")
            self.log(f"可用层级: {slide.level_dimensions}")

            # 计算切片数量
            num_tiles_x = (width + tile_size - 1) // tile_size
            num_tiles_y = (height + tile_size - 1) // tile_size
            total_tiles = num_tiles_x * num_tiles_y

            self.log(f"将切片为{tile_size}x{tile_size}的小块，共{num_tiles_x}x{num_tiles_y}={total_tiles}个切片")

            # 获取最佳读取参数
            best_level = slide.get_best_level_for_downsample(1.0)  # 获取最高分辨率层级

            # 遍历并保存每个切片
            tile_count = 0
            for y in range(0, height, tile_size):
                for x in range(0, width, tile_size):
                    # 计算实际切片大小
                    actual_width = min(tile_size, width - x)
                    actual_height = min(tile_size, height - y)

                    # 高清读取区域（使用最高分辨率）
                    tile = slide.read_region(
                        (x, y),
                        best_level,
                        (actual_width, actual_height)
                    )

                    # 高质量转换（保持色彩精度）
                    if tile.mode == 'RGBA':
                        # 创建白色背景
                        background = Image.new('RGB', tile.size, (255, 255, 255))
                        background.paste(tile, mask=tile.split()[3])  # 使用alpha通道
                        tile = background
                    elif tile.mode == 'RGBa':
                        # 处理浮点RGBa格式
                        tile = tile.convert('RGB')

                    # 保存切片
                    tile_name = f"tile_{x:05d}_{y:05d}.png"
                    tile_path = os.path.join(output_dir, tile_name)

                    # 使用PNG无损压缩
                    tile.save(
                        tile_path,
                        format='PNG',
                        compress_level=1,  # 最快压缩但无损
                        dpi=(300, 300)  # 设置高DPI
                    )

                    # 更新进度
                    tile_count += 1
                    progress = (tile_count / total_tiles) * 100
                    self.root.after(10, self.update_progress, progress)
                    self.log(f"已保存: {tile_name} ({tile_count}/{total_tiles})")

            slide.close()
            self.root.after(10, self.update_progress, 100)
            self.root.after(10, self.update_status, "处理完成！", "green")
            self.log("===== 处理完成 =====")
            self.log(f"所有切片已保存到: {output_dir}")

            # 显示完成消息
            self.root.after(100, lambda: messagebox.showinfo("完成", "SVS切片已全部完成！"))

        except Exception as e:
            error_msg = f"处理出错: {str(e)}"
            self.root.after(10, self.log, error_msg)
            self.root.after(10, self.update_status, "处理出错", "red")
            self.root.after(100, lambda: messagebox.showerror("错误", error_msg))
        finally:
            # 恢复按钮状态
            self.processing = False
            self.root.after(10, lambda: self.process_btn.config(state=tk.NORMAL))


if __name__ == "__main__":
    root = tk.Tk()
    app = SVSTilerApp(root)
    root.mainloop()