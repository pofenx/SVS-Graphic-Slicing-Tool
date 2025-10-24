import os
from pathlib import Path
import openslide
from PIL import Image


def slice_svs_to_tiles_hq(svs_path, output_dir, tile_size=1024, quality=100):
    """
    高清切片SVS文件为指定大小的小块

    参数:
        svs_path (str): SVS文件路径
        output_dir (str): 切片保存目录
        tile_size (int): 切片大小（默认1024x1024）
        quality (int): 保存质量（1-100，仅对JPEG有效）
    """
    try:
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 打开SVS文件
        slide = openslide.OpenSlide(svs_path)
        width, height = slide.dimensions

        print(f"成功打开SVS文件: {svs_path}")
        print(f"原始分辨率: {width}x{height}")
        print(f"可用层级: {slide.level_dimensions}")

        # 计算切片数量
        num_tiles_x = (width + tile_size - 1) // tile_size
        num_tiles_y = (height + tile_size - 1) // tile_size

        print(f"将切片为{tile_size}x{tile_size}的小块，共{num_tiles_x}x{num_tiles_y}个切片")

        # 获取最佳读取参数
        best_level = slide.get_best_level_for_downsample(1.0)  # 获取最高分辨率层级

        # 遍历并保存每个切片
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

                # 高质量保存
                tile_name = f"tile_{x:05d}_{y:05d}.png"  # 用5位数字编号
                tile_path = os.path.join(output_dir, tile_name)

                # 使用PNG无损压缩
                tile.save(
                    tile_path,
                    format='PNG',
                    compress_level=1,  # 最快压缩但无损
                    dpi=(300, 300)  # 设置高DPI
                )

                print(f"已保存高清切片: {tile_path}")

        slide.close()
        print("高清切片完成！")
        print(f"所有切片已保存到: {output_dir}")

    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        raise


if __name__ == "__main__":
    svs_file = r"file/1.svs"  # SVS文件路径
    output_directory = r"file/tiles"  # 切片保存目录

    # 执行高清切片
    slice_svs_to_tiles_hq(
        svs_file,
        output_directory,
        tile_size=1024,
        quality=100
    )