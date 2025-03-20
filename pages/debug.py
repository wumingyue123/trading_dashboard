import streamlit as st
from .api_tester import run_api_tests

st.set_page_config(
    page_title="Debug - Crypto Trading Dashboard",
    page_icon="🔍",
    layout="wide"
)

st.title("🔧 Debug & API Testing")

st.markdown("""
This page helps diagnose API connection issues and verify that the credentials are working correctly.
The tests will check:
- API key validity
- Endpoint accessibility
- Response data format
""")

if st.button("🔄 Run API Tests"):
    run_api_tests()

st.markdown("---")

st.subheader("📝 Session State Information")
if st.checkbox("Show Session State"):
    # Show only non-sensitive information
    safe_state = {
        key: "API Key Present" if any(cred in key.lower() for cred in ['api', 'secret', 'password']) else value
        for key, value in st.session_state.items()
    }
    st.json(safe_state)

# Show the current state of credentials
st.subheader("🔑 API Credentials Status")
if 'exchange_credentials' in st.session_state:
    creds = st.session_state.exchange_credentials
    for exchange, config in creds.items():
        st.write(f"**{exchange.capitalize()}**")
        for key in config:
            has_value = bool(config[key])
            st.write(f"- {key}: {'✅ Set' if has_value else '❌ Not Set'}")
else:
    st.warning("No API credentials found in session state")