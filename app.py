import streamlit as st
from lxml import etree
import pandas as pd
import io

# --- Core Logic Functions ---

def extract_forms_by_coverage_code_value(tree, target_code):
    """
    Search for forms where a CoverageCode field's rule value matches target_code.
    Example: Finds <public id="MLTC0107Output.CoverageCode"> with <value value="ML" />
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
        # Move up to the parent 'object' (e.g., MLTC0107Output or MLTC0107)
        # We want to find the ID of the main form object.
        current = val_elem.getparent().getparent() # This is the <public> element
        
        # Traverse up to find the main form object ID (e.g., MLTC0107)
        while current is not None:
            obj_id = current.get('id', '')
            # Form IDs in your XML usually look like MLTC0107, PSXS0146, etc.
            if obj_id and not (obj_id.endswith('Output') or obj_id.endswith('Input') or obj_id.endswith('Private')):
                found_forms.add(obj_id)
                break
            current = current.getparent()
            
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
                
                # Display results as a clean list/table
                df = pd.DataFrame(results, columns=["Form Name / Type"])
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
