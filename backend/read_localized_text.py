from typing import List, Dict, Callable
import json
import os
from xml.etree.ElementTree import parse, ParseError, Element

LOCALIZATION_PATH = "database/localization"

def get_all_data(get_function: Callable[[], Dict[str, Dict[str, str]]], language: str) -> Dict:
    data = get_function()
    replacement_tags = get_all_localization()[language]

    for key in data:
        replace_tags_with_localized_text(data, key, "name", replacement_tags)
        replace_tags_with_localized_text(data, key, "description", replacement_tags)
    
    return data

def get_all_localization() -> Dict[str, Dict[str, str]]:
    xml_dict: Dict[str, Dict[str, str]] = {}
    for root, dirs, files in os.walk(LOCALIZATION_PATH):
        for file in files:
            if file.endswith('.xml'):
                file_language, ext = os.path.splitext(file)
                file_path = os.path.join(root, file)
                try:
                    tree = parse(file_path)
                    et_root = tree.getroot()
                    localized_texts = et_root.find("LocalizedText")
                    replaced_tags = format_xml_element_into_dict(localized_texts.findall("Replace"))
                    xml_dict[file_language] = replaced_tags
                except ParseError:
                    xml_dict[file_language] = None
    return xml_dict

def format_xml_element_into_dict(replace_tags: List[Element]) -> Dict[str, str]:
    result = {}
    for replace_xml_element in replace_tags:
        tag = replace_xml_element.get("Tag")
        text = replace_xml_element.find("Text").text
        text = text.strip()
        result[tag] = text
    return result

def get_skills() -> Dict[str, Dict[str, str]]:
    try:
        with open('database/json/skills.json') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print("Error: 'skills.json' not found.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in 'skills.json'.")
    return {}

def get_cards() -> Dict[str, Dict[str, str]]:
    try:
        with open('database/json/cardbase.json') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print("Error: 'cards.json' not found.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in 'cards.json'.")
    return {}

def replace_tags_with_localized_text(
        dict: Dict[str, Dict[str, str]], 
        key: str, 
        attr: str, 
        replacement_tags: Dict[str, str]
    ) -> str:
    target_str = dict[key][attr]
    if target_str.startswith("<"):
        skill_tag = target_str[1:-1]
        if skill_tag in replacement_tags:
            dict[key][attr] = replacement_tags[skill_tag]
            return replacement_tags[skill_tag]
    return ""

if __name__ == '__main__':
    get_all_data(get_skills, "en")