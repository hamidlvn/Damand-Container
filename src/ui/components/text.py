import streamlit as st

def render_page_header(title_en: str, title_fa: str, desc_en: str, desc_fa: str):
    """
    Renders a professional, bilingual page header with consistent typography.
    """
    st.markdown(f"### {title_en} <span style='font-size: 0.75em; color: #888; font-weight: normal;'>| {title_fa}</span>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="margin-bottom: 24px; padding: 16px; border-radius: 6px; background-color: #f8f9fc; border-left: 4px solid #5a7b9e;">
        <p style="font-size: 14px; color: #2c3e50; margin-bottom: 12px; line-height: 1.5;">
            {desc_en}
        </p>
        <p style="font-size: 15px; color: #4a5568; margin: 0; line-height: 1.6; direction: rtl; text-align: right; font-family: Tahoma, 'Segoe UI', Arial, sans-serif;">
            {desc_fa}
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_section_title(title: str):
    """Renders a clean, medium-sized section header."""
    st.markdown(f"<h4 style='color: #2c3e50; margin-top: 24px; margin-bottom: 12px; font-weight: 600; font-size: 18px;'>{title}</h4>", unsafe_allow_html=True)

def render_caption(text: str):
    """Renders a subtle caption under tables or charts."""
    st.markdown(f"<p style='font-size: 12px; color: #718096; margin-top: -10px; margin-bottom: 16px; font-style: italic;'>{text}</p>", unsafe_allow_html=True)
