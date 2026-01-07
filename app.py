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
    base_name = group_name.replace("And", "")
    if base_name + "Input" not in target_ids:
        target_ids.extend([f"{base_name}Input", f"{base_name}Output"])

    for target_id in target_ids:
        obj_element = tree.find(f".//object[@id='{target_id}']")
        if obj_element is not None:
            public_fields = obj_element.findall(".//public")
            for field in public_fields:
                results.append({
                    "Field ID": field.get('id'),
                    "XPath": build_logical_xpath(field)
                })
    return results

# --- Streamlit Web UI ---

st.set_page_config(page_title="XPath Extractor", layout="wide")
st.title("📂 XML XPath Extraction Portal")

uploaded_file = st.file_uploader("Upload your Manuscript (XML)", type=["xml"])

if uploaded_file:
    try:
        tree = etree.parse(uploaded_file)
        st.success("File uploaded successfully!")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Option A: Group Extraction")
            group_input = st.text_input("Enter Group Name")
            if st.button("Extract Group"):
                data = extract_group_xpaths(tree, group_input)
                if data:
                    st.session_state['results_df'] = pd.DataFrame(data)
                else:
                    st.warning("No data found for this group.")

        with col2:
            st.subheader("Option B: Individual Fields")
            field_input = st.text_area("Enter Field IDs (one per line)")
            if st.button("Extract Fields"):
                fields = [f.strip() for f in field_input.split('\n') if f.strip()]
                data = [find_xpath_for_field(tree, f) for f in fields]
                if data:
                    st.session_state['results_df'] = pd.DataFrame(data)

        # --- Enhanced Results Display ---
        if 'results_df' in st.session_state:
            df = st.session_state['results_df']
            st.divider()
            
            # Create Tabs for different viewing modes
            tab1, tab2 = st.tabs(["📊 Interactive View", "📋 Copy-Paste View"])
            
            with tab1:
                st.dataframe(df, use_container_width=True)
            
            with tab2:
                st.info("Click the icon in the top right of the box below to copy all data at once.")
                # Convert DF to a TSV (Tab Separated) string for easy pasting into Excel
                tsv_data = df.to_csv(index=False, sep='\t')
                st.code(tsv_data, language='text')

            # --- Export Section ---
            output = io.BytesIO()
            # We use xlsxwriter for Excel export
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Results as Excel",
                data=output.getvalue(),
                file_name="extracted_xpaths.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
