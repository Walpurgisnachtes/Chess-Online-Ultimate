import json
import os
import xml.etree.ElementTree as ET

LOCALIZATION_PATH = "backend/localization"

def get_all_skills(language):
    skills = get_skills()
    replacement_tags = get_all_localization()[language]

    for skill_key in skills:
        replace_skills_with_localized_text(skills, skill_key, "name", replacement_tags)
        replace_skills_with_localized_text(skills, skill_key, "description", replacement_tags)
    
    return skills

def get_all_localization():
    xml_dict = {}
    for root, dirs, files in os.walk(LOCALIZATION_PATH):
        for file in files:
            if file.endswith('.xml'):
                file_language, ext = os.path.splitext(file)
                file_path = os.path.join(root, file)
                try:
                    tree = ET.parse(file_path)
                    et_root = tree.getroot()
                    localized_texts = et_root.find("LocalizedText")
                    replaced_tags = format_xml_replaces(localized_texts.findall("Replace"))
                    xml_dict[file_language] = replaced_tags
                except ET.ParseError:
                    xml_dict[file_language] = None
    return xml_dict

def format_xml_replaces(replace_tags):
    result = {}
    for replacement_element in replace_tags:
        tag = replacement_element.get("Tag")
        text = replacement_element.find("Text").text
        text = text.strip()
        result[tag] = text
    return result

def get_skills():
    try:
        with open('backend/json/skills.json') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print("Error: 'skills.json' not found.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in 'skills.json'.")
    return {}

def replace_skills_with_localized_text(dict, key, attr, replacement_tags):
    target_str = dict[key][attr]
    if target_str.startswith("<"):
        skill_tag = target_str[1:-1]
        if skill_tag in replacement_tags:
            dict[key][attr] = replacement_tags[skill_tag]
            return replacement_tags[skill_tag]

if __name__ == '__main__':
    get_all_skills("en")