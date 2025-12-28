"""
翻譯服務模組
"""
import os
import json
from typing import Optional

from config.settings import CACHE_FILE, MAX_TEXT_LENGTH

# 條件載入翻譯模組
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False
    print("警告: 找不到 deep-translator 模組，將跳過翻譯功能。")


class TranslationService:
    """翻譯服務類"""

    def __init__(self, cache_file: str = CACHE_FILE):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.translator = None

        if HAS_TRANSLATOR:
            try:
                self.translator = GoogleTranslator(source='auto', target='zh-TW')
            except Exception as e:
                print(f"翻譯器初始化失敗: {e}")

    def _load_cache(self) -> dict:
        """載入翻譯快取"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_cache(self) -> bool:
        """儲存翻譯快取"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"儲存快取失敗: {e}")
            return False

    def translate(self, text: str) -> str:
        """
        自動翻譯文字

        Args:
            text: 待翻譯文字

        Returns:
            str: 翻譯後的文字，若翻譯失敗則回傳原文
        """
        if not text or len(text) < 2:
            return text

        # 檢查快取
        if text in self.cache:
            return self.cache[text]

        # 無翻譯器時回傳原文
        if not self.translator:
            return text

        try:
            # 限制文字長度
            truncated = text[:MAX_TEXT_LENGTH] if len(text) > MAX_TEXT_LENGTH else text
            result = self.translator.translate(truncated)

            # 更新快取
            self.cache[text] = result
            return result
        except Exception as e:
            print(f"翻譯失敗: {e}")
            return text


# 全局翻譯服務實例
_translation_service: Optional[TranslationService] = None


def get_translator() -> TranslationService:
    """取得全局翻譯服務實例"""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def auto_translate(text: str) -> str:
    """便捷翻譯函數"""
    return get_translator().translate(text)


def save_translation_cache() -> bool:
    """儲存翻譯快取"""
    return get_translator().save_cache()
