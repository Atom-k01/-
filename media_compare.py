import os
import sys
import re
import time
from collections import defaultdict
import threading
import queue

def convert_size(size_bytes):
    """将字节转换为更友好的单位 (MB/GB)"""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"

def extract_resolution(filename):
    """从文件名中提取分辨率信息"""
    match = re.search(r'(\d{3,4}p)', filename, re.IGNORECASE)
    return match.group(1).upper() if match else "未知分辨率"

def extract_season_episode(filename):
    """从文件名中提取季集信息 (SxxExx) - 仅用于剧集模式"""
    match = re.search(r'(S\d{1,2}E\d{1,2})', filename, re.IGNORECASE)
    return match.group(0).upper() if match else None

def get_dir_structure(root_dir, mode, progress_queue):
    """获取目录结构"""
    dir_structure = defaultdict(list)
    
    # 获取所有目录列表
    all_dirs = []
    for root, dirs, files in os.walk(root_dir):
        all_dirs.append(root)
    
    for foldername in all_dirs:
        # 更新进度
        progress_queue.put(foldername)
        
        try:
            filenames = os.listdir(foldername)
        except Exception as e:
            continue
            
        rel_path = os.path.relpath(foldername, root_dir)
        
        # 电影模式：每个目录视为一个电影
        if mode == "movie":
            # 只处理直接包含视频文件的目录（一级目录）
            if os.path.dirname(rel_path) == "":
                video_files = []
                for filename in filenames:
                    filepath = os.path.join(foldername, filename)
                    if os.path.isfile(filepath) and filename.lower().endswith(('.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv')):
                        try:
                            size = os.path.getsize(filepath)
                            resolution = extract_resolution(filename)
                            video_files.append((filename, size, resolution))
                        except:
                            continue
                
                if video_files:
                    dir_structure[rel_path] = video_files
        
        # 剧集模式
        elif mode == "tv":
            for filename in filenames:
                filepath = os.path.join(foldername, filename)
                if os.path.isfile(filepath) and filename.lower().endswith(('.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv')):
                    try:
                        size = os.path.getsize(filepath)
                        episode_key = extract_season_episode(filename)
                        
                        if episode_key:
                            dir_structure[rel_path].append((filename, size, episode_key))
                    except:
                        continue
    
    # 发送完成信号
    progress_queue.put(None)
    return dir_structure

def progress_monitor(progress_queue, source_name):
    """显示扫描进度 - 仅显示动态图标"""
    spinner = ['-', '\\', '|', '/']
    spinner_idx = 0
    
    print(f"  {source_name}扫描中...", end='', flush=True)
    
    while True:
        try:
            current_dir = progress_queue.get(timeout=0.5)
            if current_dir is None:
                break
                
            # 更新旋转图标
            spinner_idx = (spinner_idx + 1) % 4
            # 清理行
            sys.stdout.write('\r\033[K')
            sys.stdout.write(f"  {spinner[spinner_idx]} {source_name}扫描中: 正在处理 {os.path.basename(current_dir)[:30]}...")
            sys.stdout.flush()
        except queue.Empty:
            continue
    
    # 扫描完成
    sys.stdout.write('\r\033[K')
    sys.stdout.write(f"  ✓ {source_name}扫描完成!\n")
    sys.stdout.flush()

def compare_media(base1, base2, log_file_path, mode):
    """比较两个目录结构并生成差异报告"""
    # 创建进度队列
    progress_queue1 = queue.Queue()
    progress_queue2 = queue.Queue()
    
    print(f"\n开始扫描整理包: {base1}")
    # 启动进度监控线程
    progress_thread1 = threading.Thread(target=progress_monitor, args=(progress_queue1, "整理包"), daemon=True)
    progress_thread1.start()
    
    # 获取目录结构
    structure1 = get_dir_structure(base1, mode, progress_queue1)
    progress_thread1.join()
    
    print(f"\n开始扫描媒体库包: {base2}")
    progress_thread2 = threading.Thread(target=progress_monitor, args=(progress_queue2, "媒体库包"), daemon=True)
    progress_thread2.start()
    structure2 = get_dir_structure(base2, mode, progress_queue2)
    progress_thread2.join()
    
    print("\n开始比较媒体库...")
    all_items = sorted(set(structure1.keys()) | set(structure2.keys()))
    
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        # 电影模式比较
        if mode == "movie":
            log_file.write(f"===== 电影比较报告 =====\n")
            log_file.write(f"整理包: {base1}\n")
            log_file.write(f"媒体库包: {base2}\n")
            log_file.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for movie_dir in sorted(all_items):
                files1 = structure1.get(movie_dir, [])
                files2 = structure2.get(movie_dir, [])
                
                # 跳过两边都没有视频文件的目录
                if not files1 and not files2:
                    continue
                    
                in_base1 = bool(files1)
                in_base2 = bool(files2)
                
                # 输出电影标题
                if not in_base1 and in_base2:
                    log_file.write(f"[电影] {movie_dir}（整理包无，媒体库包有）\n")
                    log_file.write(f"  媒体库包文件列表:\n")
                    for filename, size, resolution in files2:
                        log_file.write(f"    ├─ {filename} ({resolution}, {convert_size(size)})\n")
                    log_file.write("\n")
                    continue
                    
                if in_base1 and not in_base2:
                    log_file.write(f"[电影] {movie_dir}（整理包有，媒体库包无）\n")
                    log_file.write(f"  整理包文件列表:\n")
                    for filename, size, resolution in files1:
                        log_file.write(f"    ├─ {filename} ({resolution}, {convert_size(size)})\n")
                    log_file.write("\n")
                    continue
                    
                # 两边都有电影文件
                log_file.write(f"[电影] {movie_dir}（整理包有，媒体库包有）\n")
                
                # 找出所有文件（按分辨率分组）
                files_by_res = defaultdict(dict)
                for filename, size, resolution in files1:
                    files_by_res[resolution]["base1"] = (filename, size)
                
                for filename, size, resolution in files2:
                    if resolution in files_by_res:
                        files_by_res[resolution]["base2"] = (filename, size)
                    else:
                        files_by_res[resolution] = {"base2": (filename, size)}
                
                # 比较不同分辨率的文件
                has_differences = False
                
                # 检查整理包独有的分辨率
                for res, files in files_by_res.items():
                    if "base1" in files and "base2" not in files:
                        filename, size = files["base1"]
                        log_file.write(f"  ├─ [整理包独有] {res}: {filename} ({convert_size(size)})\n")
                        has_differences = True
                
                # 检查媒体库包独有的分辨率
                for res, files in files_by_res.items():
                    if "base2" in files and "base1" not in files:
                        filename, size = files["base2"]
                        log_file.write(f"  ├─ [媒体库包独有] {res}: {filename} ({convert_size(size)})\n")
                        has_differences = True
                
                # 检查共同分辨率但不同大小
                for res, files in files_by_res.items():
                    if "base1" in files and "base2" in files:
                        filename1, size1 = files["base1"]
                        filename2, size2 = files["base2"]
                        
                        if size1 != size2:
                            log_file.write(f"  ├─ [大小不同] {res}:\n")
                            log_file.write(f"      │ 整理包: {filename1} ({convert_size(size1)})\n")
                            log_file.write(f"      └─ 媒体库包: {filename2} ({convert_size(size2)})\n")
                            has_differences = True
                
                # 如果没有差异，输出无差异信息
                if not has_differences:
                    log_file.write(f"  └─ 所有视频文件完全一致\n")
                    
                    # 输出文件列表
                    log_file.write(f"  整理包文件列表:\n")
                    for filename, size, resolution in files1:
                        log_file.write(f"    ├─ {filename} ({resolution}, {convert_size(size)})\n")
                
                log_file.write("\n")
        
        # 剧集模式比较
        elif mode == "tv":
            log_file.write(f"===== 剧集比较报告 =====\n")
            log_file.write(f"整理包: {base1}\n")
            log_file.write(f"媒体库包: {base2}\n")
            log_file.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for dir_path in sorted(all_items):
                files1 = structure1.get(dir_path, [])
                files2 = structure2.get(dir_path, [])
                
                # 跳过两边都没有视频文件的目录
                if not files1 and not files2:
                    continue
                    
                in_base1 = bool(files1)
                in_base2 = bool(files2)
                
                # 输出目录标题
                if not in_base1 and in_base2:
                    log_file.write(f"[目录] {dir_path}（整理包无，媒体库包有）\n")
                    # 按季集分组输出
                    eps = defaultdict(list)
                    for filename, size, ep in files2:
                        eps[ep].append((filename, size))
                    
                    for ep, files in eps.items():
                        log_file.write(f"  ├─ [集] {ep}\n")
                        for filename, size in files:
                            log_file.write(f"  │   └─ {filename} ({convert_size(size)})\n")
                    log_file.write("\n")
                    continue
                    
                if in_base1 and not in_base2:
                    log_file.write(f"[目录] {dir_path}（整理包有，媒体库包无）\n")
                    # 按季集分组输出
                    eps = defaultdict(list)
                    for filename, size, ep in files1:
                        eps[ep].append((filename, size))
                    
                    for ep, files in eps.items():
                        log_file.write(f"  ├─ [集] {ep}\n")
                        for filename, size in files:
                            log_file.write(f"  │   └─ {filename} ({convert_size(size)})\n")
                    log_file.write("\n")
                    continue
                    
                # 目录在两边都存在
                log_file.write(f"[目录] {dir_path}（整理包有，媒体库包有）\n")
                
                # 按季集分组
                eps1 = defaultdict(list)
                for filename, size, ep in files1:
                    eps1[ep].append((filename, size))
                
                eps2 = defaultdict(list)
                for filename, size, ep in files2:  # 修复这里：friends2 -> files2
                    eps2[ep].append((filename, size))
                
                all_eps = sorted(set(eps1.keys()) | set(eps2.keys()))
                missing_in_base2 = set(eps1.keys()) - set(eps2.keys())
                missing_in_base1 = set(eps2.keys()) - set(eps1.keys())
                
                has_differences = False
                
                # 输出缺失的季集
                for ep in sorted(missing_in_base2):
                    log_file.write(f"  ├─ [集] {ep}（整理包有，媒体库包无）\n")
                    for filename, size in eps1[ep]:
                        log_file.write(f"  │   └─ {filename} ({convert_size(size)})\n")
                    has_differences = True
                
                for ep in sorted(missing_in_base1):
                    log_file.write(f"  ├─ [集] {ep}（整理包无，媒体库包有）\n")
                    for filename, size in eps2[ep]:
                        log_file.write(f"  │   └─ {filename} ({convert_size(size)})\n")
                    has_differences = True
                
                # 比较共同季集
                common_eps = set(eps1.keys()) & set(eps2.keys())
                for ep in sorted(common_eps):
                    files_ep1 = eps1[ep]
                    files_ep2 = eps2[ep]
                    
                    # 检查文件差异
                    file_diffs = False
                    
                    # 检查文件名和大小差异
                    for filename1, size1 in files_ep1:
                        found = False
                        for filename2, size2 in files_ep2:
                            if filename1 == filename2 and size1 == size2:
                                found = True
                                break
                        
                        if not found:
                            # 检查是否有相同分辨率但大小不同
                            res1 = extract_resolution(filename1)
                            same_res_found = False
                            for filename2, size2 in files_ep2:
                                res2 = extract_resolution(filename2)
                                if res1 == res2 and size1 != size2:
                                    log_file.write(f"  ├─ [集] {ep}（{res1}大小不同）\n")
                                    log_file.write(f"  │   ├─ 整理包: {filename1} ({convert_size(size1)})\n")
                                    log_file.write(f"  │   └─ 媒体库包: {filename2} ({convert_size(size2)})\n")
                                    same_res_found = True
                                    file_diffs = True
                                    break
                            
                            if not same_res_found:
                                log_file.write(f"  ├─ [集] {ep}（整理包独有文件）\n")
                                log_file.write(f"  │   └─ {filename1} ({convert_size(size1)})\n")
                                file_diffs = True
                    
                    # 检查媒体库包独有的文件
                    for filename2, size2 in files_ep2:
                        found = False
                        for filename1, size1 in files_ep1:
                            if filename2 == filename1 and size2 == size1:
                                found = True
                                break
                        
                        if not found:
                            # 检查是否有相同分辨率但大小不同（已处理过）
                            res2 = extract_resolution(filename2)
                            same_res_found = False
                            for filename1, size1 in files_ep1:
                                res1 = extract_resolution(filename1)
                                if res1 == res2 and size1 != size2:
                                    same_res_found = True
                                    break
                            
                            if not same_res_found:
                                log_file.write(f"  ├─ [集] {ep}（媒体库包独有文件）\n")
                                log_file.write(f"  │   └─ {filename2} ({convert_size(size2)})\n")
                                file_diffs = True
                    
                    if file_diffs:
                        has_differences = True
                
                # 如果没有差异，输出无差异信息
                if not has_differences:
                    log_file.write(f"  └─ 所有季集文件完全一致\n")
                
                log_file.write("\n")
    
    print(f"\n比较完成! 结果已保存到: {log_file_path}")

def get_input(prompt, default=None):
    """获取用户输入，支持默认值"""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    else:
        return input(prompt).strip()

def main():
    print("=" * 60)
    print("媒体库比较工具")
    print("=" * 60)
    
    # 选择模式
    mode = ""
    while mode not in ["1", "2"]:
        print("\n请选择比较模式:")
        print("  1. 剧集模式 (TV Shows)")
        print("  2. 电影模式 (Movies)")
        mode = input("请输入选择 (1/2): ").strip()
    
    mode = "tv" if mode == "1" else "movie"
    
    # 获取路径
    print("\n" + "=" * 60)
    print(f"请提供{'剧集' if mode=='tv' else '电影'}路径:")
    
    base1 = get_input("整理包路径: ")
    while not os.path.exists(base1):
        print(f"错误: 路径不存在 - {base1}")
        base1 = get_input("请重新输入整理包路径: ")
    
    base2 = get_input("媒体库包路径: ")
    while not os.path.exists(base2):
        print(f"错误: 路径不存在 - {base2}")
        base2 = get_input("请重新输入媒体库包路径: ")
    
    # 生成日志文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_filename = f"{timestamp}_{'剧集' if mode=='tv' else '电影'}比较报告.log"
    
    print("\n" + "=" * 60)
    log_dir = get_input("日志输出目录 (留空为当前目录): ", os.getcwd())
    
    # 确保目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file_path = os.path.join(log_dir, log_filename)
    
    print("\n" + "=" * 60)
    print(f"即将开始比较:")
    print(f"  模式: {'剧集' if mode=='tv' else '电影'}")
    print(f"  整理包: {base1}")
    print(f"  媒体库包: {base2}")
    print(f"  日志文件: {log_file_path}")
    print("=" * 60)
    
    input("\n按 Enter 键开始比较...")
    
    compare_media(base1, base2, log_file_path, mode)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {str(e)}")
        sys.exit(1)