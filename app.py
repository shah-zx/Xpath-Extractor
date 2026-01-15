import streamlit as st
from lxml import etree
import pandas as pd
import io

# --- Core Logic Functions ---

def extract_forms_by_coverage_code_value(tree, target_code):
    """
    Search for forms where a CoverageCode field's rule value matches target_code.
    Refines 'MLDO0106Output.CoverageCode' down to 'MLDO0106'.
    """
    found_forms = set()
    
    # XPath to find 'public' elements whose ID contains 'CoverageCode'
    # and has a <value> tag with a 'value' attribute matching the user input.
    xpath_query = (
        f"//public[contains(@id, '.CoverageCode')]"
        f"/rules/value[@value='{target_code.strip()}']"
    )
    
    matching_values = tree.xpath(xpath_query)
    
    for val_elem in matching_values:
        # The grandparent of the <value> tag is the <public> tag
        public_tag = val_elem.getparent().getparent()
        full_id = public_tag.get('id', '')
        
        if full_id:
            # 1. Split by "." to remove ".CoverageCode" -> "MLDO0106Output"
            base_name = full_id.split('.')[0]
            
            # 2. Remove "Output", "Input", or "Private" suffixes to get just the Form Name
            for suffix in ["Output", "Input", "Private"]:
                if base_name.endswith(suffix):
                    base_name = base_name[: -len(suffix)]
                    break
            
            found_forms.add(base_name)
            
    return sorted(list(found_forms))

# --- Streamlit Web UI ---

st.set_page_config(page_title="Coverage Form Finder", layout="wide")
st.title("Manuscript Coverage Search")

uploaded_file = st.file_uploader("Upload Manuscript XML", type=["xml"])

if uploaded_file:
    try:
        tree = etree.parse(uploaded_file)
        st.success("XML Loaded Successfully")

        # UI Input Section
        st.subheader("Search Forms by Coverage Code")
        cov_input = st.text_input("Enter Coverage Code (e.g., ML)", value="ML")
        
        if st.button("Find Forms"):
            results = extract_forms_by_coverage_code_value(tree, cov_input)
            
            if results:
                st.write(f"### Found {len(results)} forms for Coverage Code: **{cov_input}**")
                
                # Display results in a table
                df = pd.DataFrame(results, columns=["Form Name"])
                st.table(df)
                
                # Copy-paste section
                st.divider()
                st.subheader("Copy-Paste List")
                form_string = ", ".join(results)
                st.code(f"Forms - {form_string}", language="text")
                
            else:
                st.error(f"No forms found with a CoverageCode value of '{cov_input}'")

    except Exception as e:
        st.error(f"Error: {str(e)}")
