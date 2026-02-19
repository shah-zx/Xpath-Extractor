import streamlit as st
from lxml import etree
import pandas as pd
import io

# --- Core Logic Functions ---

def build_logical_xpath(element):
    path_segments = []
    current = element
    while current is not None:
        segment = None
        if 'path' in current.attrib:
            segment = current.get('path')
        elif current.tag == 'object' and 'id' in current.attrib:
            obj_id = current.get('id')
            if obj_id.lower() == 'data':
                segment = 'data'
            elif obj_id.lower() == 'policy':
                segment = 'policy'
            else:
                segment = obj_id
        
        if segment:
            path_segments.insert(0, segment)
        if current.tag in ('model', 'ManuScript'):
            break
        current = current.getparent()

    final_segments = []
    for s in path_segments:
        if not final_segments or s != final_segments[-1]:
            final_segments.append(s)
    return "/".join(final_segments)

def find_xpath_for_field(tree, field_name):
    try:
        xpath_query = f'//public[@id="{field_name}"]'
        elements = tree.xpath(xpath_query)
        if elements:
            return {"Field ID": field_name, "XPath": build_logical_xpath(elements[0])}
        return {"Field ID": field_name, "XPath": "NOT FOUND"}
    except Exception as e:
        return {"Field ID": field_name, "XPath": f"ERROR ({str(e)})"}

def extract_group_xpaths(tree, group_name):
    results = []
    target_ids = [f"{group_name}Input", f"{group_name}Output"]
    base_name = group_name.replace("And", "")
    if base_name + "Input" not in target_ids:
        target_ids.extend([f"{base_name}Input", f"{base_name}Output"])

    for target_id in target_ids:
        obj_element = tree.find(f".//object[@id='{target_id}']")
        if obj_element is not None:
            public_fields = obj_element.findall(".//public")
            for field in public_fields:
                results.append({
                    "Source Group": target_id,
                    "Field ID": field.get('id'),
                    "XPath": build_logical_xpath(field)
                })
    return results

def extract_forms_by_coverage_code_value(tree, target_code):
    found_forms = set()
    xpath_query = f"//public[contains(@id, '.CoverageCode')]/rules/value[@value='{target_code.strip()}']"
    matching_values = tree.xpath(xpath_query)
    for val_elem in matching_values:
        public_tag = val_elem.getparent().getparent()
        full_id = public_tag.get('id', '')
        if full_id:
            base_name = full_id.split('.')[0]
            for suffix in ["Output", "Input", "Private"]:
                if base_name.endswith(suffix):
                    base_name = base_name[: -len(suffix)]
                    break
            found_forms.add(base_name)
    return sorted(list(found_forms))

# --- Streamlit Web UI ---
st.set_page_config(page_title="Manuscript XPath Toolkit", layout="wide", page_icon="📂")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; background-color: #28a745; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("📂 Manuscript Extraction Portal")

with st.sidebar:
    st.header("Upload Settings")
    uploaded_file = st.file_uploader("Upload Manuscript (XML)", type=["xml"])

if uploaded_file:
    try:
        tree = etree.parse(uploaded_file)
        col1, col2, col3 = st.columns(3)

        with col1:
            with st.container(border=True):
                st.subheader("🔍 Coverage Search")
                cov_input = st.text_input("Coverage Code", placeholder="ML")
                if st.button("Search by Coverage"):
                    results = extract_forms_by_coverage_code_value(tree, cov_input)
                    st.session_state['results_df'] = pd.DataFrame(results, columns=["Matching Forms"]) if results else None

        with col2:
            with st.container(border=True):
                st.subheader("📦 Group Extraction")
                group_input = st.text_input("Group/Form Name", placeholder="MLTC0107")
                if st.button("Extract XPaths"):
                    data = extract_group_xpaths(tree, group_input)
                    st.session_state['results_df'] = pd.DataFrame(data) if data else None

        with col3:
            with st.container(border=True):
                st.subheader("🎯 Field Lookup")
                field_input = st.text_area("Field IDs (one per line)")
                if st.button("Lookup Fields"):
                    fields = [f.strip() for f in field_input.split('\n') if f.strip()]
                    data = [find_xpath_for_field(tree, f) for f in fields]
                    st.session_state['results_df'] = pd.DataFrame(data) if data else None

        if 'results_df' in st.session_state and st.session_state['results_df'] is not None:
            df = st.session_state['results_df']
            st.divider()
            
            # Export Section
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button(label="📥 Download Excel", data=output.getvalue(), file_name="extract.xlsx")

            tab1, tab2 = st.tabs(["📊 Interactive Table", "📋 Copy-Paste Mode"])
            with tab1:
                st.dataframe(df, use_container_width=True, hide_index=True)
            with tab2:
                st.info("Copy the block below for documentation.")
                tsv_data = df.to_csv(index=False, sep='\t')
                st.code(tsv_data, language='text')

    except Exception as e:
        st.error(f"Error: {e}")
