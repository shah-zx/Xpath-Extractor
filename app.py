import streamlit as st
from lxml import etree
import pandas as pd
import io

# --- Core Logic Functions ---

def build_logical_xpath(element):
    """
    Constructs the logical XPath by traversing upwards and collecting 
    ALL 'path' attributes and 'id' flags to handle nested 
    and inherited groups correctly.
    """
    path_segments = []
    current = element
    
    while current is not None:
        # Check for 'path' attribute (crucial for nested/inherited groups)
        if 'path' in current.attrib:
            path_segments.insert(0, current.get('path'))
        
        # Check for root-level identifiers (data or policy)
        elif current.tag == 'object' and 'id' in current.attrib:
            object_id = current.get('id').lower()
            if object_id in ['data', 'policy']:
                path_segments.insert(0, object_id)
        
        # Stop if we hit the top-level container
        elif current.tag in ('model', 'ManuScript'):
            break
            
        current = current.getparent()
    
    # Filter out empty segments and join with slashes
    return "/".join([seg for seg in path_segments if seg])

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
                    "Source Group": target_id,
                    "Field ID": field.get('id'),
                    "XPath": build_logical_xpath(field)
                })
    return results

def extract_forms_by_coverage_code_value(tree, target_code):
    """Search for forms where a CoverageCode field's rule value matches target_code."""
    found_forms = set()
    xpath_query = (
        f"//public[contains(@id, '.CoverageCode')]"
        f"/rules/value[@value='{target_code.strip()}']"
    )
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

st.set_page_config(page_title="Manuscript XPath Toolkit", layout="wide", page_icon="🧬")

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; background-color: #28a745; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("📂 Manuscript Extraction Portal")
st.markdown("---")

# Sidebar for File Upload
with st.sidebar:
    st.header("Upload Settings")
    uploaded_file = st.file_uploader("Upload Manuscript (XML)", type=["xml"])
    if uploaded_file:
        st.success("XML File Ready")

if uploaded_file:
    try:
        tree = etree.parse(uploaded_file)
        
        # Dashboard Layout
        col1, col2, col3 = st.columns(3)

        with col1:
            with st.container(border=True):
                st.subheader("🔍 Coverage Search")
                st.caption("Find forms by Coverage Code (e.g., ML)")
                cov_input = st.text_input("Coverage Code", placeholder="ML")
                if st.button("Search by Coverage"):
                    results = extract_forms_by_coverage_code_value(tree, cov_input)
                    if results:
                        st.session_state['results_df'] = pd.DataFrame(results, columns=["Matching Forms"])
                    else:
                        st.warning(f"No forms found for '{cov_input}'")

        with col2:
            with st.container(border=True):
                st.subheader("📦 Group Extraction")
                st.caption("Extract all XPaths for a Form/Group")
                group_input = st.text_input("Group/Form Name", placeholder="MLTC0107")
                if st.button("Extract XPaths"):
                    data = extract_group_xpaths(tree, group_input)
                    if data:
                        st.session_state['results_df'] = pd.DataFrame(data)
                    else:
                        st.warning("Group not found.")

        with col3:
            with st.container(border=True):
                st.subheader("🎯 Field Lookup")
                st.caption("Find XPaths for specific Field IDs")
                field_input = st.text_area("Field IDs (one per line)", placeholder="MLTC0107Output.FormName")
                if st.button("Lookup Fields"):
                    fields = [f.strip() for f in field_input.split('\n') if f.strip()]
                    data = [find_xpath_for_field(tree, f) for f in fields]
                    if data:
                        st.session_state['results_df'] = pd.DataFrame(data)

        # --- Enhanced Results Display ---
        if 'results_df' in st.session_state:
            df = st.session_state['results_df']
            st.divider()
            
            res_col, exp_col = st.columns([3, 1])
            with res_col:
                st.subheader("📄 Extraction Results")
            with exp_col:
                # Export Section
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Download Excel",
                    data=output.getvalue(),
                    file_name="manuscript_extract.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Tabbed interface for Interactive View vs Copy-Paste Mode
            tab1, tab2 = st.tabs(["📊 Interactive Table", "📋 Copy-Paste Mode"])
            
            with tab1:
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            with tab2:
                st.info("Click the 'Copy' icon in the top-right of the box below to copy all data at once.")
                if "Matching Forms" in df.columns:
                    form_list = ", ".join(df["Matching Forms"].tolist())
                    st.code(f"Forms - {form_list}", language='text')
                else:
                    # Convert to TSV (Tab Separated) so it pastes into Excel columns automatically
                    tsv_data = df.to_csv(index=False, sep='\t')
                    st.code(tsv_data, language='text')

    except Exception as e:
        st.error(f"Critical Error: {e}")
else:
    st.info("Please upload a Manuscript XML file from the sidebar to begin.")
