import xml.etree.ElementTree as ET
import glob
import re

tree = ET.parse('/home/vvro/src/odoo-dev/industry/construction_developer/data/ir_model_fields.xml')
fields_studio = []
for record in tree.findall('.//record'):
    field_name = ""
    model_name = ""
    for field in record.findall("field[@name='name']"):
        field_name = field.text
    for field in record.findall("field[@name='model']"):
        model_name = field.text
    if field_name and model_name:
        fields_studio.append((model_name, field_name))

# Get fields from python files
python_files = glob.glob('/home/vvro/src/odoo-dev/famebuilders/famebuilders/addons/construction_developer/models/*.py')
fields_native = set()
for pf in python_files:
    with open(pf, 'r') as f:
        content = f.read()
        model_name = ""
        for line in content.split('\n'):
            model_match = re.search(r'_name\s*=\s*[\'"]([^\'"]+)[\'"]|_inherit\s*=\s*[\'"]([^\'"]+)[\'"]', line)
            if model_match:
                model_name = model_match.group(1) or model_match.group(2)
            
            field_match = re.search(r'^\s+([a-zA-Z0-9_]+)\s*=\s*fields\.', line)
            if model_match and field_match:
                fields_native.add((model_name, field_match.group(1)))
            elif model_name and field_match:
                fields_native.add((model_name, field_match.group(1)))

print("Fields in Studio:")
for model, field in sorted(fields_studio):
    print(f"  {model} : {field}")

print("\nMissing Fields (mapped from x_* to *_ without x_studio_ or x_):")
# Remove x_studio_ or x_ prefix
for model, field in sorted(fields_studio):
    native_field = re.sub(r'^x_studio_|^x_', '', field)
    native_model = re.sub(r'^x_', 'construction.', model) # Best guess mapping
    # Special cases handling could be added here
    if (model, native_field) not in fields_native and (native_model, native_field) not in fields_native:
        print(f"  Studio {model}.{field} -> Expected {native_model}.{native_field}")

