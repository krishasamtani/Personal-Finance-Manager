"""Small shared Streamlit helpers."""
import matplotlib.pyplot as plt
import streamlit as st

import config


def show_fig(fig):
    st.pyplot(fig)
    plt.close(fig)


def money(x):
    return f"{config.CURRENCY_SYMBOL}{x:,.0f}"
