from PIL import Image
from pathlib import Path
import sys
import os

# 指定输入和输出路径
RESOURCES_DIR = Path(__file__).parent
DEFAULT_OUTPUT = RESOURCES_DIR / "icon.ico"

def convert_to_ico(image_path, ico_path=DEFAULT_OUTPUT):
    """将图片转换为ICO格式，支持 JPEG/JPG/PNG 等格式"""
    try:
        # 转换路径为Path对象并解析绝对路径
        image_path = Path(image_path).resolve()
        
        if not image_path.exists():
            print(f"❌ 错误：找不到文件 {image_path}")
            return False
            
        # 打开图片
        img = Image.open(image_path)
        
        # 如果是JPEG格式，转换为RGBA
        if img.format in ('JPEG', 'JPG'):
            img = img.convert('RGBA')
        
        # 确保图片是正方形
        size = max(img.size)
        new_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        
        # 将原图居中粘贴
        paste_x = (size - img.size[0]) // 2
        paste_y = (size - img.size[1]) // 2
        new_img.paste(img, (paste_x, paste_y))
        
        # 转换为多种尺寸的图标
        icon_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
        new_img.save(ico_path, format='ICO', sizes=icon_sizes)
        
        print(f"✅ 图标已成功保存到: {ico_path}")
        return True
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python turn.py <图片路径>")
        print("支持格式: JPEG, JPG, PNG")
        print(f"当前目录: {os.getcwd()}")
        print("示例: python turn.py ./icon.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    convert_to_ico(image_path)