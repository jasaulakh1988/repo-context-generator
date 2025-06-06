#!/usr/bin/env python3
"""
Repo Context Generator - Generate AI-friendly repository context

A universal tool to generate comprehensive context files from any repository
for use with AI assistants like ChatGPT, Claude, etc.

Author: Your Name
License: MIT
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, List, Any, Optional, Tuple
import mimetypes

__version__ = "1.0.0"

class RepoContextGenerator:
    """Universal repository context generator for AI assistants"""
    
    def __init__(self, repo_path: str, output_file: str = "CONTEXT.md", 
                 max_file_size: int = 10000, max_total_size: int = 100000):
        self.repo_path = Path(repo_path).resolve()
        self.output_file = output_file
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size
        self.total_size = 0
        self.context_parts = []
        
        # Project type indicators
        self.project_indicators = {
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile', 'poetry.lock'],
            'javascript': ['package.json', 'yarn.lock', 'package-lock.json'],
            'typescript': ['tsconfig.json', 'package.json'],
            'java': ['pom.xml', 'build.gradle', 'build.gradle.kts', 'settings.gradle'],
            'go': ['go.mod', 'go.sum'],
            'rust': ['Cargo.toml', 'Cargo.lock'],
            'ruby': ['Gemfile', 'Gemfile.lock', '.ruby-version'],
            'php': ['composer.json', 'composer.lock'],
            'csharp': ['*.csproj', '*.sln', 'packages.config'],
            'cpp': ['CMakeLists.txt', 'Makefile', '*.cpp', '*.h'],
            'terraform': ['*.tf', 'terragrunt.hcl', '*.tfvars'],
            'kubernetes': ['k8s/*.yaml', 'k8s/*.yml', 'kubernetes/*.yaml'],
            'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
            'ansible': ['ansible.cfg', 'playbook.yml', 'requirements.yml'],
        }
        
        # Important files to always include
        self.important_files = [
            'README.md', 'README.rst', 'README.txt', 'README',
            'LICENSE', 'LICENSE.md', 'LICENSE.txt',
            'CONTRIBUTING.md', 'CHANGELOG.md', 'CHANGELOG',
            '.env.example', '.env.sample',
            'Makefile', 'makefile',
            '.github/workflows/*.yml', '.gitlab-ci.yml',
            'Jenkinsfile', 'azure-pipelines.yml',
        ]
        
        # Directories to skip
        self.skip_dirs = {
            '.git', '.svn', '.hg', 'node_modules', 'vendor', 
            'venv', 'env', '.env', '__pycache__', '.pytest_cache',
            'target', 'build', 'dist', 'out', '.terraform',
            '.terragrunt-cache', 'coverage', '.next', '.nuxt',
            '.idea', '.vscode', 'logs', 'tmp', 'temp',
        }
        
        # File extensions to skip
        self.skip_extensions = {
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
            '.class', '.jar', '.war', '.exe', '.bin',
            '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
            '.mp3', '.mp4', '.avi', '.mov', '.pdf',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.log', '.bak', '.swp', '.tmp', '.cache',
            '.min.js', '.min.css', '.map',
        }

    def detect_project_types(self) -> List[str]:
        """Detect project types based on characteristic files"""
        detected = []
        
        for proj_type, indicators in self.project_indicators.items():
            for indicator in indicators:
                if '*' in indicator:
                    if list(self.repo_path.glob(indicator)):
                        detected.append(proj_type)
                        break
                elif (self.repo_path / indicator).exists():
                    detected.append(proj_type)
                    break
                    
        return detected

    def get_directory_structure(self, max_depth: int = 4) -> str:
        """Generate a tree structure of the repository"""
        tree_lines = []
        
        def build_tree(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
                
            try:
                items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
                
                for i, item in enumerate(items):
                    # Skip hidden files/dirs except important ones
                    if item.name.startswith('.') and item.name not in ['.github', '.gitlab-ci.yml', '.env.example']:
                        continue
                        
                    # Skip excluded directories
                    if item.name in self.skip_dirs:
                        continue
                        
                    # Skip files with excluded extensions
                    if item.is_file() and item.suffix in self.skip_extensions:
                        continue
                    
                    is_last = i == len(items) - 1
                    current = "└── " if is_last else "├── "
                    tree_lines.append(f"{prefix}{current}{item.name}")
                    
                    if item.is_dir() and depth < max_depth:
                        extension = "    " if is_last else "│   "
                        build_tree(item, prefix + extension, depth + 1)
                        
            except PermissionError:
                pass
        
        tree_lines.append(self.repo_path.name + "/")
        build_tree(self.repo_path)
        
        # Limit tree size
        if len(tree_lines) > 150:
            tree_lines = tree_lines[:150] + ["... (truncated)"]
            
        return "\n".join(tree_lines)

    def get_file_content(self, file_path: Path, max_lines: int = 50) -> Optional[str]:
        """Safely read file content with size limits"""
        try:
            # Check file size first
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                return f"(File too large: {file_size:,} bytes)"
                
            # Try to read as text
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            if len(lines) > max_lines:
                return '\n'.join(lines[:max_lines]) + f"\n\n... (truncated, {len(lines) - max_lines} more lines)"
            
            return content
            
        except Exception as e:
            return f"(Error reading file: {str(e)})"

    def extract_package_info(self) -> Dict[str, Any]:
        """Extract package/dependency information based on project type"""
        info = {}
        
        # Python
        if (self.repo_path / "requirements.txt").exists():
            reqs = (self.repo_path / "requirements.txt").read_text().split('\n')
            deps = [r.strip() for r in reqs if r.strip() and not r.startswith('#')]
            info['python_requirements'] = deps[:20]
            
        if (self.repo_path / "pyproject.toml").exists():
            content = (self.repo_path / "pyproject.toml").read_text()
            if '[project]' in content:
                info['python_project'] = "pyproject.toml found"
                
        # Node.js
        if (self.repo_path / "package.json").exists():
            try:
                pkg = json.loads((self.repo_path / "package.json").read_text())
                info['node_package'] = {
                    'name': pkg.get('name', 'Unknown'),
                    'version': pkg.get('version', 'Unknown'),
                    'description': pkg.get('description', ''),
                    'scripts': list(pkg.get('scripts', {}).keys())[:10],
                    'dependencies': list(pkg.get('dependencies', {}).keys())[:15],
                    'devDependencies': list(pkg.get('devDependencies', {}).keys())[:10],
                }
            except:
                info['node_package'] = "package.json found but couldn't parse"
                
        # Java
        if (self.repo_path / "pom.xml").exists():
            info['java_maven'] = "pom.xml found"
            
        if (self.repo_path / "build.gradle").exists():
            info['java_gradle'] = "build.gradle found"
            
        # Go
        if (self.repo_path / "go.mod").exists():
            content = (self.repo_path / "go.mod").read_text().split('\n')
            if content:
                info['go_module'] = content[0].replace('module ', '').strip()
                
        return info

    def get_git_info(self) -> Dict[str, str]:
        """Extract git repository information"""
        git_info = {}
        
        try:
            # Check if it's a git repository
            subprocess.run(['git', 'rev-parse'], cwd=self.repo_path, 
                         capture_output=True, check=True)
            
            # Get current branch
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.repo_path, capture_output=True, text=True
            )
            git_info['branch'] = result.stdout.strip()
            
            # Get remote URL
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=self.repo_path, capture_output=True, text=True
            )
            git_info['remote'] = result.stdout.strip()
            
            # Get last commit
            result = subprocess.run(
                ['git', 'log', '-1', '--oneline'],
                cwd=self.repo_path, capture_output=True, text=True
            )
            git_info['last_commit'] = result.stdout.strip()
            
            # Get recent commits
            result = subprocess.run(
                ['git', 'log', '--oneline', '-10'],
                cwd=self.repo_path, capture_output=True, text=True
            )
            git_info['recent_commits'] = result.stdout.strip()
            
            # Get changed files
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path, capture_output=True, text=True
            )
            changed = result.stdout.strip()
            if changed:
                git_info['changed_files'] = len(changed.split('\n'))
            
        except subprocess.CalledProcessError:
            git_info['error'] = "Not a git repository"
        except FileNotFoundError:
            git_info['error'] = "Git not installed"
            
        return git_info

    def find_entry_points(self) -> List[Tuple[str, str]]:
        """Find common entry point files"""
        entry_points = []
        
        patterns = [
            # Python
            ('Python', ['main.py', 'app.py', 'run.py', 'manage.py', '__main__.py', 'cli.py']),
            # JavaScript/Node
            ('JavaScript', ['index.js', 'app.js', 'server.js', 'main.js', 'index.ts']),
            # Java
            ('Java', ['**/Main.java', '**/Application.java', 'src/main/java/**/*Application.java']),
            # Go
            ('Go', ['main.go', 'cmd/*/main.go']),
            # Rust
            ('Rust', ['src/main.rs', 'main.rs']),
            # C#
            ('C#', ['Program.cs', '**/Program.cs']),
            # PHP
            ('PHP', ['index.php', 'app.php']),
        ]
        
        for lang, files in patterns:
            for pattern in files:
                if '*' in pattern:
                    matches = list(self.repo_path.glob(pattern))[:3]
                    for match in matches:
                        entry_points.append((lang, str(match.relative_to(self.repo_path))))
                else:
                    file_path = self.repo_path / pattern
                    if file_path.exists():
                        entry_points.append((lang, pattern))
                        
        return entry_points

    def add_section(self, title: str, content: str):
        """Add a section to the context output"""
        self.context_parts.append(f"\n## {title}\n")
        self.context_parts.append(content)
        self.total_size += len(title) + len(content)

    def generate_context(self) -> str:
        """Generate the complete context document"""
        # Header
        project_types = self.detect_project_types()
        header = f"""# Repository Context

**Generated by:** Repo Context Generator v{__version__}  
**Generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Repository:** {self.repo_path.name}  
**Path:** {self.repo_path}  
**Detected Types:** {', '.join(project_types) if project_types else 'Generic'}

---

This context file provides a comprehensive overview of the repository structure and contents
for use with AI assistants.

"""
        self.context_parts.append(header)

        # Project Structure
        self.add_section("Project Structure", f"```\n{self.get_directory_structure()}\n```")

        # Git Information
        git_info = self.get_git_info()
        if git_info and 'error' not in git_info:
            git_section = []
            if 'branch' in git_info:
                git_section.append(f"**Current Branch:** {git_info['branch']}")
            if 'remote' in git_info:
                git_section.append(f"**Remote:** {git_info['remote']}")
            if 'last_commit' in git_info:
                git_section.append(f"**Last Commit:** {git_info['last_commit']}")
            if 'changed_files' in git_info:
                git_section.append(f"**Uncommitted Changes:** {git_info['changed_files']} files")
            if 'recent_commits' in git_info:
                git_section.append(f"\n### Recent Commits\n```\n{git_info['recent_commits']}\n```")
                
            self.add_section("Git Information", '\n'.join(git_section))

        # Package Information
        package_info = self.extract_package_info()
        if package_info:
            self.add_section("Package Information", f"```json\n{json.dumps(package_info, indent=2)}\n```")

        # Entry Points
        entry_points = self.find_entry_points()
        if entry_points:
            ep_content = []
            for lang, file in entry_points:
                ep_content.append(f"- **{lang}:** `{file}`")
            self.add_section("Entry Points", '\n'.join(ep_content))

        # Important Files
        self.add_section("Key Files", "")
        
        for pattern in self.important_files:
            if self.total_size > self.max_total_size * 0.8:  # Stop at 80% of max size
                self.context_parts.append("\n*(Reached size limit, some files omitted)*\n")
                break
                
            if '*' in pattern:
                files = list(self.repo_path.glob(pattern))[:3]
                for file in files:
                    self._add_file_content(file)
            else:
                file_path = self.repo_path / pattern
                if file_path.exists():
                    self._add_file_content(file_path)

        # Configuration Files
        config_files = self._find_config_files()
        if config_files and self.total_size < self.max_total_size * 0.9:
            self.add_section("Configuration Files", "")
            for file in config_files[:10]:
                if self.total_size > self.max_total_size * 0.9:
                    break
                self._add_file_content(file)

        # Source Code Sample
        if self.total_size < self.max_total_size * 0.9:
            self._add_source_samples(project_types)

        # Footer
        footer = f"\n---\n\n*Context generation complete. Total size: {self.total_size:,} characters*\n"
        self.context_parts.append(footer)

        return ''.join(self.context_parts)

    def _add_file_content(self, file_path: Path):
        """Add file content to context"""
        relative_path = file_path.relative_to(self.repo_path)
        content = self.get_file_content(file_path)
        
        if content and self.total_size + len(content) < self.max_total_size:
            # Determine language for syntax highlighting
            lang = self._get_language_for_file(file_path)
            
            self.context_parts.append(f"\n### {relative_path}\n")
            self.context_parts.append(f"```{lang}\n{content}\n```\n")
            self.total_size += len(content) + 100

    def _get_language_for_file(self, file_path: Path) -> str:
        """Determine language for syntax highlighting"""
        ext_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.go': 'go', '.rs': 'rust', '.rb': 'ruby',
            '.php': 'php', '.cs': 'csharp', '.cpp': 'cpp', '.c': 'c',
            '.h': 'c', '.hpp': 'cpp', '.swift': 'swift', '.kt': 'kotlin',
            '.r': 'r', '.R': 'r', '.sql': 'sql', '.sh': 'bash',
            '.yml': 'yaml', '.yaml': 'yaml', '.json': 'json',
            '.xml': 'xml', '.html': 'html', '.css': 'css',
            '.md': 'markdown', '.rst': 'rst', '.tex': 'latex',
            '.tf': 'hcl', '.dockerfile': 'dockerfile', '.Dockerfile': 'dockerfile',
            '.gradle': 'gradle', '.Makefile': 'makefile', '.makefile': 'makefile',
        }
        
        suffix = file_path.suffix.lower()
        return ext_map.get(suffix, 'text')

    def _find_config_files(self) -> List[Path]:
        """Find configuration files"""
        config_patterns = [
            '*.config', '*.conf', 'config.*', 'settings.*',
            '.eslintrc*', '.prettierrc*', 'tsconfig.json',
            'webpack.config.js', 'babel.config.js', 'jest.config.js',
            '.flake8', 'setup.cfg', 'tox.ini', 'pytest.ini',
        ]
        
        config_files = []
        for pattern in config_patterns:
            config_files.extend(self.repo_path.glob(pattern))
            
        return config_files[:20]  # Limit to 20 config files

    def _add_source_samples(self, project_types: List[str]):
        """Add sample source code based on project type"""
        if not project_types:
            return
            
        self.add_section("Source Code Samples", "")
        
        # Define source patterns for each project type
        source_patterns = {
            'python': ['**/*.py'],
            'javascript': ['**/*.js', '**/*.jsx'],
            'typescript': ['**/*.ts', '**/*.tsx'],
            'java': ['**/*.java'],
            'go': ['**/*.go'],
            'rust': ['**/*.rs'],
            'csharp': ['**/*.cs'],
            'cpp': ['**/*.cpp', '**/*.h'],
        }
        
        for proj_type in project_types[:2]:  # Limit to first 2 project types
            if proj_type in source_patterns:
                patterns = source_patterns[proj_type]
                
                for pattern in patterns:
                    files = []
                    for f in self.repo_path.glob(pattern):
                        # Skip test files and vendored code
                        if any(skip in str(f) for skip in ['test', 'vendor', 'node_modules', '__pycache__']):
                            continue
                        if f.is_file() and f.stat().st_size < 50000:  # Skip large files
                            files.append(f)
                            
                    # Add up to 3 sample files
                    for file in sorted(files)[:3]:
                        if self.total_size > self.max_total_size * 0.95:
                            return
                        self._add_file_content(file)

    def save(self) -> Path:
        """Generate and save the context file"""
        output_path = self.repo_path / self.output_file
        
        print(f"🔍 Analyzing repository: {self.repo_path.name}")
        print(f"📁 Path: {self.repo_path}")
        
        context = self.generate_context()
        
        output_path.write_text(context, encoding='utf-8')
        
        print(f"\n✅ Context file generated successfully!")
        print(f"📄 Output: {output_path}")
        print(f"📏 Size: {len(context):,} characters")
        print(f"🎯 Detected types: {', '.join(self.detect_project_types())}")
        
        return output_path


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate AI-friendly context from any repository',
        epilog='Example: repo-context-generator /path/to/repo -o context.md'
    )
    
    parser.add_argument(
        'repo_path',
        nargs='?',
        default='.',
        help='Path to repository (default: current directory)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='CONTEXT.md',
        help='Output file name (default: CONTEXT.md)'
    )
    
    parser.add_argument(
        '--max-file-size',
        type=int,
        default=10000,
        help='Maximum characters per file (default: 10000)'
    )
    
    parser.add_argument(
        '--max-total-size',
        type=int,
        default=100000,
        help='Maximum total context size (default: 100000)'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    args = parser.parse_args()
    
    # Validate repository path
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"❌ Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
        
    if not repo_path.is_dir():
        print(f"❌ Error: Path is not a directory: {repo_path}")
        sys.exit(1)
    
    # Generate context
    try:
        generator = RepoContextGenerator(
            repo_path=str(repo_path),
            output_file=args.output,
            max_file_size=args.max_file_size,
            max_total_size=args.max_total_size
        )
        
        generator.save()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
