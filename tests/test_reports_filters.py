from inventory_app.gui.reports.reports_page import ReportsPage


def test_usage_filter_visibility_and_items(qtbot):
    """Ensure the usage filter type includes an "All" option and the value combo
    appears only for Grade Level or Section selections with proper default items.
    """
    page = ReportsPage()
    qtbot.addWidget(page)
    page.show()

    # First combo should include the explicit All option
    assert page.usage_filter_type_combo.itemText(0) == "All Grades & Sections"

    # Selecting All should hide the second dropdown
    page.usage_filter_type_combo.setCurrentIndex(0)
    assert not page.usage_filter_value_combo.isVisible()

    # Switch the usage report type to 'Usage by Grade Level' so the grade/section widget is shown
    idx_usage_grade = page.usage_report_type.findData("grade_level")
    assert idx_usage_grade != -1
    page.usage_report_type.setCurrentIndex(idx_usage_grade)
    assert page.usage_grade_section_widget.isVisible()

    # Selecting Grade Level should show the second dropdown with 'All Grades' as first item
    idx_grade = page.usage_filter_type_combo.findText("Grade Level")
    assert idx_grade != -1
    page.usage_filter_type_combo.setCurrentIndex(idx_grade)
    assert page.usage_filter_value_combo.isVisible()
    assert page.usage_filter_value_combo.itemText(0) == "All Grades"

    # Selecting Section should show the second dropdown with 'All Sections' as first item
    idx_section = page.usage_filter_type_combo.findText("Section")
    assert idx_section != -1
    page.usage_filter_type_combo.setCurrentIndex(idx_section)
    assert page.usage_filter_value_combo.isVisible()
    assert page.usage_filter_value_combo.itemText(0) == "All Sections"
