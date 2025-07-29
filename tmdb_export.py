import argparse
import json
import os
import time
import requests
from typing import Dict, Any, Optional, List, Tuple

# 模板结构定义
TEMPLATES = {
    "movie": {
        "id": 0,
        "imdb_id": "",
        "title": "",
        "original_title": "",
        "overview": "",
        "tagline": "",
        "release_date": "",
        "vote_average": 0.0,
        "production_countries": [],
        "production_companies": [],
        "genres": [],
        "casts": {"cast": [], "crew": []},
        "releases": {"countries": []},
        "belongs_to_collection": None,
        "trailers": {"youtube": []}
    },
    "series": {
        "id": 0,
        "name": "",
        "original_name": "",
        "overview": "",
        "vote_average": 0.0,
        "episode_run_time": [],
        "first_air_date": "1970-01-01T00:00:00.000Z",
        "last_air_date": "1970-01-01T00:00:00.000Z",
        "status": "",
        "networks": [],
        "genres": [],
        "external_ids": {"imdb_id": "", "tvrage_id": None, "tvdb_id": None},
        "videos": {"results": []},
        "content_ratings": {"results": []},
        "credits": {"cast": []}
    },
    "season": {
        "name": "",
        "overview": "",
        "air_date": "1970-01-01T00:00:00.000Z",
        "external_ids": {"tvdb_id": None},
        "credits": {"cast": [], "crew": []}
    },
    "episode": {
        "name": "",
        "overview": "",
        "videos": {"results": []},
        "external_ids": {"tvdb_id": None, "tvrage_id": None, "imdb_id": ""},
        "air_date": "1970-01-01T00:00:00.000Z",
        "vote_average": 0.0,
        "credits": {"cast": [], "guest_stars": [], "crew": []}
    },
    "collection": {
        "id": 0,
        "name": "",
        "overview": ""
    }
}

class TMDBExporter:
    def __init__(self, api_key: str, api_version: str = "v3"):
        self.base_url = f"https://api.themoviedb.org/3"
        self.api_key = api_key
        self.session = requests.Session()
        self.session.params = {"api_key": self.api_key, "language": "zh-CN"}
        
    def fetch_data(self, endpoint: str, params: Optional[Dict] = None, max_retries: int = 5) -> Optional[Dict]:
        """带指数退避重试机制的请求函数"""
        url = f"{self.base_url}{endpoint}"
        retries = 0
        delay = 1
        
        while retries < max_retries:
            try:
                response = self.session.get(url, params=params or {})
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, json.JSONDecodeError) as e:
                print(f"请求失败: {e} (尝试 {retries+1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
                retries += 1
        print(f"错误: 无法获取数据 {endpoint}")
        return None
    
    def filter_data(self, data: Dict, template: Dict) -> Dict:
        """根据模板过滤数据"""
        filtered = {}
        for key, default in template.items():
            if key in data:
                # 处理嵌套结构
                if isinstance(default, dict) and isinstance(data[key], dict):
                    filtered[key] = self.filter_data(data[key], default)
                # 处理空值
                elif data[key] is None:
                    filtered[key] = default
                else:
                    filtered[key] = data[key]
            else:
                filtered[key] = default
        return filtered
    
    def export_movie(self, tmdb_id: int, output_dir: str):
        """导出电影元数据"""
        print(f"\n开始导出电影 ID: {tmdb_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取基础数据
        movie_data = self.fetch_data(f"/movie/{tmdb_id}")
        if not movie_data:
            print(f"错误: 无法获取电影基础数据 (ID: {tmdb_id})")
            return
        
        # 获取额外数据
        credits = self.fetch_data(f"/movie/{tmdb_id}/credits") or {}
        releases = self.fetch_data(f"/movie/{tmdb_id}/release_dates") or {}
        videos = self.fetch_data(f"/movie/{tmdb_id}/videos") or {}
        
        # 合并数据
        combined = {
            **movie_data,
            "casts": credits,
            "releases": {"countries": [r for r in releases.get("results", [])]},
            "trailers": {"youtube": [v for v in videos.get("results", []) if v.get("site") == "YouTube"]}
        }
        
        # 过滤并保存
        filtered = self.filter_data(combined, TEMPLATES["movie"])
        with open(os.path.join(output_dir, "all.json"), "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
        print(f"电影数据已保存至: {os.path.join(output_dir, 'all.json')}")
    
    def export_series(self, tmdb_id: int, output_dir: str, 
                     combine_seasons: bool = False, 
                     season_mapping: Optional[Dict[int, int]] = None):
        """导出剧集元数据
        
        Args:
            combine_seasons: 是否将所有季合并为一季
            season_mapping: 季号映射字典 {原始季号: 目标季号}
        """
        print(f"\n开始导出剧集 ID: {tmdb_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取剧集基础数据
        series_data = self.fetch_data(f"/tv/{tmdb_id}")
        if not series_data:
            print(f"错误: 无法获取剧集基础数据 (ID: {tmdb_id})")
            return
        
        # 获取额外数据
        credits = self.fetch_data(f"/tv/{tmdb_id}/credits") or {}
        external_ids = self.fetch_data(f"/tv/{tmdb_id}/external_ids") or {}
        content_ratings = self.fetch_data(f"/tv/{tmdb_id}/content_ratings") or {}
        videos = self.fetch_data(f"/tv/{tmdb_id}/videos") or {}
        
        # 合并数据
        combined = {
            **series_data,
            "credits": {"cast": credits.get("cast", [])},
            "external_ids": external_ids,
            "content_ratings": content_ratings,
            "videos": videos
        }
        
        # 过滤并保存剧集数据
        filtered_series = self.filter_data(combined, TEMPLATES["series"])
        with open(os.path.join(output_dir, "series.json"), "w", encoding="utf-8") as f:
            json.dump(filtered_series, f, indent=2, ensure_ascii=False)
        print(f"剧集数据已保存至: {os.path.join(output_dir, 'series.json')}")
        
        # 导出所有季
        seasons = [s for s in series_data.get("seasons", []) if s.get("season_number", 0) > 0]
        
        if combine_seasons:
            print(f"合并所有季为一季")
            self.export_combined_seasons(tmdb_id, seasons, output_dir, season_mapping)
        else:
            for season in seasons:
                orig_season_num = season["season_number"]
                target_season_num = season_mapping.get(orig_season_num, orig_season_num) if season_mapping else orig_season_num
                self.export_season(tmdb_id, orig_season_num, output_dir, target_season_num)
    
    def export_combined_seasons(self, series_id: int, seasons: List[Dict], output_dir: str, 
                              season_mapping: Optional[Dict[int, int]] = None):
        """将所有季合并为一季导出"""
        # 确定目标季号
        target_season_num = season_mapping.get(1, 1) if season_mapping else 1
        
        # 创建合并后的季元数据
        combined_season = {
            "name": "全集",
            "overview": "所有季合并",
            "air_date": seasons[0]["air_date"] if seasons else "1970-01-01T00:00:00.000Z",
            "external_ids": {"tvdb_id": None},
            "credits": {"cast": [], "crew": []}
        }
        
        # 保存合并后的季数据
        season_file = os.path.join(output_dir, f"season-{target_season_num}.json")
        with open(season_file, "w", encoding="utf-8") as f:
            json.dump(combined_season, f, indent=2, ensure_ascii=False)
        print(f"合并季数据已保存至: {season_file}")
        
        # 导出所有集（合并后）
        global_episode_number = 1
        for season in seasons:
            season_number = season["season_number"]
            season_data = self.fetch_data(f"/tv/{series_id}/season/{season_number}")
            if not season_data:
                print(f"警告: 无法获取季数据 (季: {season_number})")
                continue
            
            episodes = season_data.get("episodes", [])
            for episode in episodes:
                episode_number = episode["episode_number"]
                success = self.export_episode(
                    series_id, season_number, episode_number, output_dir,
                    target_season=target_season_num, target_episode=global_episode_number
                )
                if success:
                    global_episode_number += 1
    
    def export_season(self, series_id: int, orig_season_num: int, output_dir: str, target_season_num: int):
        """导出单季元数据
        
        Args:
            orig_season_num: TMDB中的原始季号
            target_season_num: 要导出为的目标季号
        """
        print(f"  导出季 #{orig_season_num} -> 季 #{target_season_num}")
        
        # 获取季数据
        season_data = self.fetch_data(f"/tv/{series_id}/season/{orig_season_num}")
        if not season_data:
            print(f"警告: 无法获取季数据 (季: {orig_season_num})")
            return
        
        # 获取额外数据
        credits = self.fetch_data(f"/tv/{series_id}/season/{orig_season_num}/credits") or {}
        external_ids = self.fetch_data(f"/tv/{series_id}/season/{orig_season_num}/external_ids") or {}
        
        # 合并数据
        combined = {
            **season_data,
            "credits": credits,
            "external_ids": external_ids
        }
        
        # 过滤并保存
        filtered_season = self.filter_data(combined, TEMPLATES["season"])
        season_file = os.path.join(output_dir, f"season-{target_season_num}.json")
        with open(season_file, "w", encoding="utf-8") as f:
            json.dump(filtered_season, f, indent=2, ensure_ascii=False)
        
        # 导出所有集
        for episode in season_data.get("episodes", []):
            episode_number = episode["episode_number"]
            self.export_episode(series_id, orig_season_num, episode_number, output_dir,
                               target_season=target_season_num)
    
    def export_episode(self, series_id: int, orig_season_num: int, orig_episode_num: int, 
                      output_dir: str, target_season: Optional[int] = None, 
                      target_episode: Optional[int] = None) -> bool:
        """导出单集元数据
        
        Args:
            orig_season_num: TMDB中的原始季号
            orig_episode_num: TMDB中的原始集号
            target_season: 要导出为的目标季号
            target_episode: 要导出为的目标集号
            
        返回: 是否成功导出
        """
        # 确定文件名
        if target_season is not None and target_episode is not None:
            filename = f"season-{target_season}-episode-{target_episode}.json"
        elif target_season is not None:
            filename = f"season-{target_season}-episode-{orig_episode_num}.json"
        else:
            filename = f"season-{orig_season_num}-episode-{orig_episode_num}.json"
        
        print(f"    导出集: S{orig_season_num}E{orig_episode_num} -> {filename}")
        
        # 获取集数据
        endpoint = f"/tv/{series_id}/season/{orig_season_num}/episode/{orig_episode_num}"
        episode_data = self.fetch_data(endpoint)
        if not episode_data:
            print(f"警告: 无法获取集数据 (S{orig_season_num}E{orig_episode_num})")
            return False
        
        # 获取额外数据
        credits = self.fetch_data(f"{endpoint}/credits") or {}
        external_ids = self.fetch_data(f"{endpoint}/external_ids") or {}
        videos = self.fetch_data(f"{endpoint}/videos") or {}
        
        # 合并数据
        combined = {
            **episode_data,
            "credits": credits,
            "external_ids": external_ids,
            "videos": videos
        }
        
        # 过滤并保存
        filtered_episode = self.filter_data(combined, TEMPLATES["episode"])
        ep_file = os.path.join(output_dir, filename)
        with open(ep_file, "w", encoding="utf-8") as f:
            json.dump(filtered_episode, f, indent=2, ensure_ascii=False)
        return True
    
    def export_collection(self, tmdb_id: int, output_dir: str):
        """导出合集元数据"""
        print(f"\n开始导出合集 ID: {tmdb_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        collection_data = self.fetch_data(f"/collection/{tmdb_id}")
        if not collection_data:
            print(f"错误: 无法获取合集数据 (ID: {tmdb_id})")
            return
        
        filtered = self.filter_data(collection_data, TEMPLATES["collection"])
        with open(os.path.join(output_dir, "all.json"), "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
        print(f"合集数据已保存至: {os.path.join(output_dir, 'all.json')}")


def parse_season_mapping(mapping_str: str) -> Dict[int, int]:
    """解析季号映射字符串，格式为 '原季号=新季号,原季号=新季号'"""
    if not mapping_str:
        return {}
    
    mapping = {}
    for pair in mapping_str.split(','):
        if '=' in pair:
            orig, target = pair.split('=')
            try:
                mapping[int(orig.strip())] = int(target.strip())
            except ValueError:
                print(f"警告: 无效的季号映射 '{pair}'，将被忽略")
    return mapping


def main():
    parser = argparse.ArgumentParser(description="TMDB元数据导出工具")
    parser.add_argument("tmdbid", type=int, help="TMDB ID")
    parser.add_argument("apikey", type=str, help="TMDB API密钥")
    parser.add_argument("output", type=str, help="输出目录路径")
    parser.add_argument("--type", choices=["auto", "movie", "tv", "collection"], 
                        default="auto", help="内容类型 (默认自动检测)")
    parser.add_argument("--apiversion", choices=["v3", "v4"], default="v3", 
                        help="API版本 (默认v3)")
    parser.add_argument("--combine-seasons", action="store_true", 
                        help="将所有季合并为一季（仅对剧集有效）")
    parser.add_argument("--season-mapping", type=str, default="",
                        help="季号映射，格式 '原季号=新季号,原季号=新季号' (例如 '1=2')")
    
    args = parser.parse_args()
    exporter = TMDBExporter(args.apikey, args.apiversion)
    
    # 解析季号映射
    season_mapping = parse_season_mapping(args.season_mapping)
    
    # 创建类型目录
    output_dir = os.path.join(args.output, f"{args.tmdbid}")
    
    if args.type == "auto":
        # 尝试检测类型
        movie_test = exporter.fetch_data(f"/movie/{args.tmdbid}")
        if movie_test:
            exporter.export_movie(args.tmdbid, os.path.join(output_dir, "movie"))
            return
        
        tv_test = exporter.fetch_data(f"/tv/{args.tmdbid}")
        if tv_test:
            exporter.export_series(args.tmdbid, os.path.join(output_dir, "series"), 
                                  combine_seasons=args.combine_seasons,
                                  season_mapping=season_mapping)
            return
        
        collection_test = exporter.fetch_data(f"/collection/{args.tmdbid}")
        if collection_test:
            exporter.export_collection(args.tmdbid, os.path.join(output_dir, "collection"))
            return
        
        print("错误: 无法确定内容类型，请手动指定 --type 参数")
    
    elif args.type == "movie":
        exporter.export_movie(args.tmdbid, os.path.join(output_dir, "movie"))
    
    elif args.type == "tv":
        exporter.export_series(args.tmdbid, os.path.join(output_dir, "series"), 
                              combine_seasons=args.combine_seasons,
                              season_mapping=season_mapping)
    
    elif args.type == "collection":
        exporter.export_collection(args.tmdbid, os.path.join(output_dir, "collection"))


if __name__ == "__main__":
    main()