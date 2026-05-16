# utils/quran_extractor.py
import re
from utils.quran_surahs import SURAH_COMPLETE_MAP

def get_surah_by_name(name):
    """دریافت اطلاعات سوره با نام فارسی یا عربی"""
    name = name.strip()
    for surah_name, info in SURAH_COMPLETE_MAP.items():
        if surah_name == name or info["ar"] == name:
            return {
                "persian_name": surah_name,
                "arabic_name": info["ar"],
                "number": info["number"]
            }
    return None

def get_surah_by_number(number):
    """دریافت نام سوره با شماره"""
    for surah_name, info in SURAH_COMPLETE_MAP.items():
        if info["number"] == number:
            return {
                "persian_name": surah_name,
                "arabic_name": info["ar"],
                "number": number
            }
    return None

def search_surah_in_text(text):
    """جستجوی نام سوره در یک متن"""
    for surah_name, info in SURAH_COMPLETE_MAP.items():
        if surah_name in text or info["ar"] in text:
            return get_surah_by_name(surah_name)
    return None

def extract_surah_from_question(question):
    """استخراج اطلاعات سوره از سوال کاربر"""
    question = question.strip()
    
    # الگوی 1: سوره بقره
    match1 = re.search(r'سوره\s+([^\s\d]+)', question)
    if match1:
        return search_surah_in_text(match1.group(1))
    
    # الگوی 2: سوره 2
    match2 = re.search(r'سوره\s*(\d+)', question)
    if match2:
        return get_surah_by_number(int(match2.group(1)))
    
    # الگوی 3: فقط نام سوره (بدون کلمه سوره)
    for surah_name in SURAH_COMPLETE_MAP.keys():
        if surah_name in question:
            return get_surah_by_name(surah_name)
    
    return None

def extract_verse_info(question):
    """
    استخراج اطلاعات آیه و سوره از سوال کاربر
    return: dict یا None
    """
    result = {
        "surah": None,
        "verse_number": None,
        "has_verse": False
    }
    
    question = question.strip()
    
    # الگوی 1: آیه 26 سوره بقره
    pattern1 = re.search(r'آیه\s*(\d+)\s*سوره\s*(.+?)(?:\s|$)', question)
    if pattern1:
        result["verse_number"] = int(pattern1.group(1))
        surah_query = pattern1.group(2).strip()
        result["surah"] = search_surah_in_text(surah_query)
        result["has_verse"] = True
        return result
    
    # الگوی 2: سوره 2 آیه 255
    pattern2 = re.search(r'سوره\s*(\d+)\s*آیه\s*(\d+)', question)
    if pattern2:
        surah_num = int(pattern2.group(1))
        result["verse_number"] = int(pattern2.group(2))
        result["surah"] = get_surah_by_number(surah_num)
        result["has_verse"] = True
        return result
    
    # الگوی 3: فقط آیه 112 سوره اخلاص
    pattern3 = re.search(r'آیه\s*(\d+)\s*(?:از\s*)?سوره\s*(.+)', question)
    if pattern3:
        result["verse_number"] = int(pattern3.group(1))
        surah_query = pattern3.group(2).strip()
        result["surah"] = search_surah_in_text(surah_query)
        result["has_verse"] = True
        return result
    
    # الگوی 4: فقط نام سوره (بدون آیه)
    surah = extract_surah_from_question(question)
    if surah:
        result["surah"] = surah
        result["has_verse"] = False
        return result
    
    return None