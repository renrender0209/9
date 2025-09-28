"""
Invidiousインスタンスリストの管理とフォールバック機能
"""
import random
import logging
import requests
from typing import List, Optional, Dict

class InvidiousInstanceManager:
    """複数のInvidiousインスタンスを管理するクラス"""
    
    def __init__(self):
        # 主要なInvidiousインスタンス（アタッチされたファイルから）
        self.instances = [
            "https://yt.omada.cafe",  # 最優先
            "https://invidious.privacyredirect.com",
            "https://invidious.technicalvoid.dev",
            "https://invidious.darkness.services",
            "https://invidious.nikkosphere.com",
            "https://invidious.schenkel.eti.br",
            "https://invidious.tiekoetter.com",
            "https://invidious.perennialte.ch",
            "https://invidious.reallyaweso.me",
            "https://invidious.private.coffee",
            "https://invidious.privacydev.net",
            "https://invidious.adminforge.de",
            "https://invidious.drgns.space",
            "https://invidious.catspeed.cc",
            "https://invidious.jing.rocks",
            "https://invidious.nerdvpn.de",
            "https://invidious.lunar.icu",
            "https://inv.us.projectsegfault",
            "https://inv.in.projectsegfault",
            "https://invidious.baczek.me",
            "https://inv.everypizza.im",
            "https://inv.stealthy.club",
            "https://inv.clovius.club",
            "https://invidious.f5.si",
            "https://iv.melmac.space",
            "https://inv.nadeko.net",
            "https://iv.ggtyler.dev",
            "https://yt.funami.tech",
            "https://inv.tux.pizza",
            "https://inv.vern.cc",
            "https://iv.duti.dev",
            "https://lekker.gay",
            "https://inv.vy.ci",
            "https://y.com.sb",
            "https://vid.puffyan.us",
            "https://yt.artemislena.eu",
            "https://youtube.076.ne.jp",
            "https://invidious.osi.kr",
            "https://yewtu.be",
            "https://invidio.xamh.de",
            "https://invidious.kavin.rocks",
            "https://invidious.flokinet.to",
            "https://invidious.sethforprivacy.com",
            "https://invidious.esmailelbob.xyz",
            "https://ytb.trom.tf",
            "https://invidious.domain.glass",
            "https://tube.cthd.icu",
            "https://invidious.garudalinux.org",
            "https://youtube.owacon.moe",
            "https://invidious.tinfoil-hat.net",
            "https://invidious.no-logs.com",
            "https://vid.priv.au",
            "https://not-ytb.blocus.ch",
            "https://inv.creller.net",
            "https://inv.zzls.xyz",
            "https://yt.floss.media",
            "https://invidious.slipfox.xyz",
            "https://inv.citw.lgbt",
            "https://invidious.io.lol",
            "https://yt.oelrichsgarcia.de",
            "https://iv.nboeck.de",
            "https://invidious.protokolla.fi",
            "https://invidious.fi",
            "https://invidious.takebackourtech.org",
            "https://anontube.lvkaszus.pl",
            "https://invidious.asir.dev",
            "https://invidious.fdn.fr",
            "https://iv.datura.network",
            "https://inv.pistasjis.net",
            "https://invidious.pavot.ca",
            "https://yt.cdaut.de",
            "https://yt.drgnz.club",
            "https://yt.chaotic.ninja",
            "https://i.redsnake.io",
            "https://watch.supernets.org",
            "https://invidious.qwik.space",
            "https://inv.odyssey346.dev",
            "https://invidious.mutahar.rocks",
            "https://invidious.projectsegfau.lt",
            "https://invidious.weblibre.org",
            "https://watch.thekitty.zone"
        ]
        self.timeout = 5
        self.failed_instances = set()  # 失敗したインスタンスを追跡
        
    def get_working_instance(self) -> Optional[str]:
        """動作中のインスタンスを取得"""
        # 失敗していないインスタンスから選択
        available_instances = [inst for inst in self.instances if inst not in self.failed_instances]
        
        if not available_instances:
            # 全て失敗した場合は失敗リストをリセット
            self.failed_instances.clear()
            available_instances = self.instances.copy()
        
        # ランダムに選択（負荷分散）
        return random.choice(available_instances)
        
    def mark_failed(self, instance_url: str):
        """失敗したインスタンスをマーク"""
        self.failed_instances.add(instance_url)
        logging.warning(f"Invidiousインスタンス失敗マーク: {instance_url}")
        
    def get_video_data(self, video_id: str) -> Optional[Dict]:
        """複数のインスタンスから動画データを取得（フォールバック付き）"""
        for attempt in range(3):  # 最大3回試行
            instance = self.get_working_instance()
            if not instance:
                break
                
            try:
                url = f"{instance}/api/v1/videos/{video_id}"
                logging.info(f"Invidiousリクエスト試行 {attempt + 1}: {url}")
                
                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    logging.info(f"✅ Invidious成功: {instance}")
                    return data
                else:
                    logging.warning(f"Invidious HTTPエラー {response.status_code}: {instance}")
                    self.mark_failed(instance)
                    
            except Exception as e:
                logging.warning(f"Invidiousエラー {instance}: {e}")
                self.mark_failed(instance)
                
        logging.error("全てのInvidiousインスタンスが失敗しました")
        return None
        
    def get_video_comments(self, video_id: str) -> Optional[Dict]:
        """複数のインスタンスから動画コメントを取得"""
        for attempt in range(3):
            instance = self.get_working_instance()
            if not instance:
                break
                
            try:
                url = f"{instance}/api/v1/comments/{video_id}"
                logging.info(f"Invidiousコメントリクエスト試行 {attempt + 1}: {url}")
                
                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    logging.info(f"✅ Invidiousコメント成功: {instance}")
                    return data
                else:
                    logging.warning(f"Invidiousコメント HTTPエラー {response.status_code}: {instance}")
                    self.mark_failed(instance)
                    
            except Exception as e:
                logging.warning(f"Invidiousコメントエラー {instance}: {e}")
                self.mark_failed(instance)
                
        logging.error("全てのInvidiousインスタンスでコメント取得が失敗しました")
        return None
        
    def get_trending_videos(self) -> Optional[List[Dict]]:
        """トレンド動画を取得"""
        for attempt in range(3):
            instance = self.get_working_instance()
            if not instance:
                break
                
            try:
                url = f"{instance}/api/v1/trending"
                logging.info(f"Invidiousトレンドリクエスト試行 {attempt + 1}: {url}")
                
                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    logging.info(f"✅ Invidiousトレンド成功: {instance} - {len(data)} 件")
                    return data
                else:
                    logging.warning(f"Invidiousトレンド HTTPエラー {response.status_code}: {instance}")
                    self.mark_failed(instance)
                    
            except Exception as e:
                logging.warning(f"Invidiousトレンドエラー {instance}: {e}")
                self.mark_failed(instance)
                
        logging.error("全てのInvidiousインスタンスでトレンド取得が失敗しました")
        return None

# グローバルインスタンス
invidious_manager = InvidiousInstanceManager()