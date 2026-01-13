import streamlit as st
from lxml import etree
import pandas as pd
import io

# --- Core Logic Functions ---

def build_logical_xpath(element):
    """Constructs the logical XPath from the XML structure."""
    path_segments = []
    current = element
    while current is not None:
        segment = None
        if 'path' in current.attrib:
            segment = current.get('path')
        elif current.tag == 'object' and 'id' in current.attrib:
            object_id = current.get('id')
            if object_id.lower() == 'data':
                segment = 'data'
            elif object_id.lower() == 'policy':
                segment = 'policy'
        elif current.tag in ('model', 'ManuScript'):
            break
        if segment:
            path_segments.insert(0, segment)
        current = current.getparent()
    return "/".join(path_segments)

def find_xpath_for_field(tree, field_name):
    """Finds XPath for a single field ID."""
    try:
        xpath_query = f'//public[@id="{field_name}"]'
        elements = tree.xpath(xpath_query)
        if elements:
            return {"Field ID": field_name, "XPath": build_logical_xpath(elements[0])}
        return {"Field ID": field_name, "XPath": "NOT FOUND"}
    except Exception as e:
        return {"Field ID": field_name, "XPath": f"ERROR ({str(e)})"}

def extract_group_xpaths(tree, group_name):
    """Extracts XPaths for all public fields in a group."""
    results = []
    target_ids = [f"{group_name}Input", f"{group_name}Output"]
    # Logic to handle naming variations like "And" removal 
    base_name = group_name.replace("And", "")
    if base_name + "Input" not in target_ids:
        target_ids.extend([f"{base_name}Input", f"{base_name}Output"])

    for target_id in target_ids:
        obj_element = tree.find(f".//object[@id='{target_id}']")
        if obj_element is not None:
            public_fields = obj_element.findall(".//public")
            for field in public_fields:
                results.append({
                    "Group/Form": group_name,
                    "Field ID": field.get('id'),
                    "XPath": build_logical_xpath(field)
                })
    return results

def extract_by_coverage_code(tree, coverage_code):
    """Finds forms by coverage code and extracts XPaths for their groups."""
    all_results = []
    # Find all Form tags where CoverageCode matches input
    forms = tree.xpath(f"//Form[CoverageCode='{coverage_code}']")
    
    for form in forms:
        form_name = form.findtext("FormName")
        # Assuming the 'Type' or a specific ID relates to the group name
        # We will try to extract group info based on the Form's Type tag
        form_type = form.findtext("Type")
        
        if form_type:
            group_data = extract_group_xpaths(tree, form_type)
            for entry in group_data:
                entry["Form Name"] = form_name  # Add Form Name to the results
                all_results.append(entry)
                
    return all_results

# --- Streamlit Web UI ---

st.set_page_config(page_title="XPath Extractor", layout="wide")
st.title("XML XPath Extraction Portal")

uploaded_file = st.file_uploader("Upload your Manuscript (XML)", type=["xml"])

if uploaded_file:
    try:
        tree = etree.parse(uploaded_file)
        st.success("File uploaded successfully!")

        # Layout for three options now
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("Option A: Group")
            group_input = st.text_input("Enter Group Name")
            if st.button("Extract Group"):
                data = extract_group_xpaths(tree, group_input)
                if data: st.session_state['results_df'] = pd.DataFrame(data)

        with col2:
            st.subheader("Option B: Fields")
            field_input = st.text_area("Enter Field IDs (one per line)")
            if st.button("Extract Fields"):
                fields = [f.strip() for f in field_input.split('\n') if f.strip()]
                data = [find_xpath_for_field(tree, f) for f in fields]
                if data: st.session_state['results_df'] = pd.DataFrame(data)

        with col3:
            st.subheader("Option C: Coverage Code")
            cov_input = st.text_input("Enter Coverage Code (e.g., ML)")
            if st.button("Extract by Coverage"):
                data = extract_by_coverage_code(tree, cov_input)
                if data:
                    st.session_state['results_df'] = pd.DataFrame(data)
                else:
                    st.warning(f"No forms found for coverage code: {cov_input}")

        # --- Results Display ---
        if 'results_df' in st.session_state:
            df = st.session_state['results_df']
            st.divider()
            
            tab1, tab2 = st.tabs(["Interactive View", "Copy-Paste View"])
            with tab1:
                st.dataframe(df, use_container_width=True)
            with tab2:
                tsv_data = df.to_csv(index=False, sep='\t')
                st.code(tsv_data, language='text')

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="Download Results as Excel",
                data=output.getvalue(),
                file_name="extracted_xpaths.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
