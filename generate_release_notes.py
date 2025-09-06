#!/usr/bin/env python3
"""
Release Notes Generation Script

This script provides easy commands for generating release notes
for the Laboratory Inventory Management System.
"""

import os
import sys
from datetime import datetime
from release_notes_generator import ReleaseNotesGenerator


def generate_current_release_notes():
    """Generate release notes for the current state of the repository."""
    print("🔍 Generating release notes for current repository state...")
    
    generator = ReleaseNotesGenerator()
    
    # Generate version based on date
    version = f"v{datetime.now().strftime('%Y.%m.%d')}"
    
    print(f"📝 Creating release notes for version: {version}")
    
    # Generate markdown version
    print("📄 Generating Markdown format...")
    generator.save_release_notes(
        "RELEASE_NOTES.md", 
        format="markdown", 
        version=version
    )
    
    # Generate JSON version
    print("📊 Generating JSON format...")
    generator.save_release_notes(
        "RELEASE_NOTES.json", 
        format="json", 
        version=version
    )
    
    print("✅ Release notes generated successfully!")
    print("📁 Files created:")
    print("   - RELEASE_NOTES.md (Markdown format)")
    print("   - RELEASE_NOTES.json (JSON format)")


def generate_release_notes_since_tag(tag):
    """Generate release notes since a specific git tag."""
    print(f"🔍 Generating release notes since tag: {tag}")
    
    generator = ReleaseNotesGenerator()
    
    # Generate version based on date
    version = f"v{datetime.now().strftime('%Y.%m.%d')}"
    
    print(f"📝 Creating release notes for version: {version}")
    
    # Generate markdown version
    generator.save_release_notes(
        f"RELEASE_NOTES_{version}.md", 
        format="markdown", 
        version=version,
        since=tag
    )
    
    print(f"✅ Release notes generated since {tag}!")


def print_release_notes_preview():
    """Print a preview of release notes to console."""
    print("🔍 Generating release notes preview...")
    
    generator = ReleaseNotesGenerator()
    version = f"Preview {datetime.now().strftime('%Y.%m.%d %H:%M')}"
    
    notes = generator.generate_markdown_release_notes(version=version)
    
    print("=" * 80)
    print(notes)
    print("=" * 80)


def main():
    """Main function with command line interface."""
    if len(sys.argv) < 2:
        print("📋 Release Notes Generator for Laboratory Inventory Management System")
        print("\nUsage:")
        print("  python generate_release_notes.py current    - Generate notes for current state")
        print("  python generate_release_notes.py since <tag> - Generate notes since git tag")
        print("  python generate_release_notes.py preview    - Preview notes in console")
        print("\nExamples:")
        print("  python generate_release_notes.py current")
        print("  python generate_release_notes.py since v1.0.0")
        print("  python generate_release_notes.py preview")
        return
    
    command = sys.argv[1].lower()
    
    if command == "current":
        generate_current_release_notes()
    elif command == "since" and len(sys.argv) > 2:
        tag = sys.argv[2]
        generate_release_notes_since_tag(tag)
    elif command == "preview":
        print_release_notes_preview()
    else:
        print("❌ Invalid command. Use 'current', 'since <tag>', or 'preview'")


if __name__ == "__main__":
    main()