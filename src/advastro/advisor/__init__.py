"""Advisor (phase 1): turns measurements and the user profile into recommendations.

Design: rules are data (TOML files in advisor/rules/), each with a condition,
a tool-neutral recommendation, an explanation template and a confidence.
Translators in advisor/translators/ map neutral advice to PixInsight, Siril
and other tools. Every recommendation carries the measured value, the
threshold and the reason.
"""
