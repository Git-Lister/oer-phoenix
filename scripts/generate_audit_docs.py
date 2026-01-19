#!/usr/bin/env python
"""
Automated audit documentation generator for Django projects.

This script extracts current state from a Django project and regenerates
audit documentation files (.txt) in .continue/agents/ directory.

Supports:
- Migrations
- Models (Django ORM)
- Views & API endpoints
- URL patterns
- Management commands
- Celery tasks
- Templates & static files
- Custom extractors (harvesters, services, etc.)

Usage:
    python generate_audit_docs.py [--project-root /path/to/project] [--app resources]
    
Environment:
    Set DJANGO_SETTINGS_MODULE or run within a Django manage.py context.
"""

import os
import sys
import re
import ast
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass


@dataclass
class AuditConfig:
    """Configuration for audit generation."""
    project_root: Path
    django_app: str = "resources"
    continue_agents_dir: Optional[Path] = None
    
    def __post_init__(self):
        if self.continue_agents_dir is None:
            self.continue_agents_dir = self.project_root / ".continue" / "agents"


class DjangoProjectAuditor:
    """Extracts Django project metadata for audit documentation."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self.app_dir = config.project_root / config.django_app
        self.migrations_dir = self.app_dir / "migrations"
        self.templates_dir = config.project_root / "templates"
        self.static_dir = config.project_root / "static"
        self.management_commands_dir = self.app_dir / "management" / "commands"
        self.services_dir = self.app_dir / "services"
        self.harvesters_dir = self.app_dir / "harvesters"
    
    def extract_migrations(self) -> List[str]:
        """Extract migration file names."""
        if not self.migrations_dir.exists():
            return []
        
        migrations = []
        for file in sorted(self.migrations_dir.glob("*.py")):
            if file.name != "__init__.py":
                migrations.append(file.name)
        return migrations
    
    def extract_models(self) -> Dict[str, Dict]:
        """Extract Django model classes and their fields."""
        models_file = self.app_dir / "models.py"
        if not models_file.exists():
            return {}
        
        models = {}
        with open(models_file, 'r') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's likely a model (inherits from Model or has Meta)
                base_names = [b.id if isinstance(b, ast.Name) else 
                             (b.attr if isinstance(b, ast.Attribute) else str(b))
                             for b in node.bases]
                
                if any('Model' in str(b) for b in base_names):
                    models[node.name] = {
                        'bases': base_names,
                        'docstring': ast.get_docstring(node) or '',
                        'line': node.lineno
                    }
        
        return models
    
    def extract_views(self, module_name: str = "views") -> List[Tuple[str, str]]:
        """Extract view functions/classes from views module."""
        views_file = self.app_dir / f"{module_name}.py"
        if not views_file.exists():
            return []
        
        views = []
        with open(views_file, 'r') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node) or ''
                views.append((node.name, docstring.split('\n')[0] if docstring else ''))
            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ''
                views.append((node.name, docstring.split('\n')[0] if docstring else ''))
        
        return views
    
    def extract_url_patterns(self) -> List[Tuple[str, str]]:
        """Extract URL patterns from urls.py."""
        urls_file = self.app_dir / "urls.py"
        if not urls_file.exists():
            return []
        
        patterns = []
        with open(urls_file, 'r') as f:
            content = f.read()
        
        # Simple regex-based extraction of path/url patterns
        # Matches: path('route', view, name='pattern_name')
        pattern_regex = r"(?:path|url|re_path)\(['\"]([^'\"]*)['\"],\s*([^,]+),\s*name=['\"]([^'\"]*)['\"]"
        
        for match in re.finditer(pattern_regex, content):
            route, view, name = match.groups()
            patterns.append((f"{route}", f"{view.strip()} → {name}"))
        
        return patterns
    
    def extract_management_commands(self) -> List[str]:
        """Extract management command file names."""
        if not self.management_commands_dir.exists():
            return []
        
        commands = []
        for file in sorted(self.management_commands_dir.glob("*.py")):
            if file.name != "__init__.py":
                commands.append(file.name.replace('.py', ''))
        return commands
    
    def extract_celery_tasks(self) -> List[Tuple[str, str]]:
        """Extract Celery @shared_task definitions from tasks.py."""
        tasks_file = self.app_dir / "tasks.py"
        if not tasks_file.exists():
            return []
        
        tasks = []
        with open(tasks_file, 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if '@shared_task' in line or '@app.task' in line:
                # Look for the next function definition
                for j in range(i+1, min(i+10, len(lines))):
                    if 'def ' in lines[j]:
                        func_name = re.search(r'def\s+(\w+)', lines[j])
                        if func_name:
                            docstring = ''
                            if j+1 < len(lines) and '"""' in lines[j+1]:
                                docstring = lines[j+1].strip('"""').strip()
                            tasks.append((func_name.group(1), docstring))
                        break
        
        return tasks
    
    def extract_templates(self) -> Dict[str, List[str]]:
        """Extract template file structure."""
        if not self.templates_dir.exists():
            return {}
        
        templates = {}
        for root, dirs, files in os.walk(self.templates_dir):
            rel_path = Path(root).relative_to(self.templates_dir)
            category = str(rel_path) if str(rel_path) != '.' else 'root'
            
            template_files = [f for f in files if f.endswith(('.html', '.txt', '.xml'))]
            if template_files:
                templates[category] = sorted(template_files)
        
        return templates
    
    def extract_static_files(self) -> Dict[str, List[str]]:
        """Extract static file structure."""
        if not self.static_dir.exists():
            return {}
        
        statics = {}
        for root, dirs, files in os.walk(self.static_dir):
            rel_path = Path(root).relative_to(self.static_dir)
            category = str(rel_path) if str(rel_path) != '.' else 'root'
            
            if files:
                statics[category] = sorted(files)
        
        return statics
    
    def extract_harvesters(self) -> Dict[str, List[str]]:
        """Extract harvester implementations and base classes."""
        if not self.harvesters_dir.exists():
            return {}
        
        harvesters = {
            'base': [],
            'implementations': [],
            'utilities': []
        }
        
        for file in sorted(self.harvesters_dir.glob("*.py")):
            if file.name == "__init__.py":
                continue
            
            if 'base' in file.name:
                harvesters['base'].append(file.name)
            elif file.name in ['utils.py', 'preset_configs.py', 'ingestion.py', 'api.py', 'oaipmh.py', 'base.py']:
                harvesters['utilities'].append(file.name)
            else:
                harvesters['implementations'].append(file.name)
        
        return harvesters
    
    def extract_services(self) -> List[str]:
        """Extract service module files."""
        if not self.services_dir.exists():
            return []
        
        services = []
        for file in sorted(self.services_dir.glob("*.py")):
            if file.name != "__init__.py":
                services.append(file.name)
        return services


class AuditDocumentGenerator:
    """Generates .txt audit documentation files."""
    
    def __init__(self, config: AuditConfig, auditor: DjangoProjectAuditor):
        self.config = config
        self.auditor = auditor
        self.output_dir = config.continue_agents_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_migrations_txt(self) -> None:
        """Generate all_migrations.txt."""
        migrations = self.auditor.extract_migrations()
        
        content = f"""# Django Migrations Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}
App: {self.config.django_app}

## Total Migrations: {len(migrations)}

"""
        
        for i, migration in enumerate(migrations, 1):
            # Extract description from migration filename
            description = migration.replace('.py', '').replace('_', ' ')
            content += f"{i}. {migration}\n   ({description})\n\n"
        
        output_file = self.output_dir / "all_migrations.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_models_txt(self) -> None:
        """Generate extracted_models.txt."""
        models = self.auditor.extract_models()
        
        content = f"""# Django Models Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}
App: {self.config.django_app}

## Total Models: {len(models)}

"""
        
        for model_name, model_info in sorted(models.items()):
            content += f"### {model_name}\n"
            if model_info['docstring']:
                content += f"   {model_info['docstring']}\n"
            content += f"   Base classes: {', '.join(model_info['bases'])}\n"
            content += f"   Defined at line: {model_info['line']}\n\n"
        
        output_file = self.output_dir / "extracted_models.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_views_txt(self) -> None:
        """Generate url_views.txt."""
        views = self.auditor.extract_views('views')
        
        content = f"""# Django Views & API Endpoints Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}
App: {self.config.django_app}

## Total Views/Functions: {len(views)}

"""
        
        for view_name, docstring in views:
            content += f"def {view_name}(request):\n"
            if docstring:
                content += f"    {docstring}\n"
            content += "\n"
        
        output_file = self.output_dir / "url_views.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_urls_txt(self) -> None:
        """Generate url_patterns.txt."""
        patterns = self.auditor.extract_url_patterns()
        
        content = f"""# URL Patterns Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}
App: {self.config.django_app}

## Total URL Patterns: {len(patterns)}

"""
        
        content += "| Route | View/Handler |\n"
        content += "|-------|------------------|\n"
        
        for route, view_info in patterns:
            content += f"| `{route}` | {view_info} |\n"
        
        output_file = self.output_dir / "url_patterns.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_management_commands_txt(self) -> None:
        """Generate management commands reference."""
        commands = self.auditor.extract_management_commands()
        
        content = f"""# Django Management Commands Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}
App: {self.config.django_app}

## Total Commands: {len(commands)}

"""
        
        for i, cmd in enumerate(commands, 1):
            content += f"{i}. python manage.py {cmd}\n"
        
        output_file = self.output_dir / "management_commands.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_celery_tasks_txt(self) -> None:
        """Generate celery tasks reference."""
        tasks = self.auditor.extract_celery_tasks()
        
        content = f"""# Celery Tasks Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}
App: {self.config.django_app}

## Total @shared_task Decorators: {len(tasks)}

"""
        
        for task_name, docstring in tasks:
            content += f"### {task_name}()\n"
            if docstring:
                content += f"   {docstring}\n"
            content += "\n"
        
        output_file = self.output_dir / "celery_tasks.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_templates_txt(self) -> None:
        """Generate all_templates.txt."""
        templates = self.auditor.extract_templates()
        
        content = f"""# Django Templates Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}

## Total Template Categories: {len(templates)}

"""
        
        total_templates = 0
        for category in sorted(templates.keys()):
            files = templates[category]
            total_templates += len(files)
            content += f"\n### {category}/\n"
            for file in files:
                content += f"   - {file}\n"
        
        content += f"\n**Total Templates: {total_templates}**\n"
        
        output_file = self.output_dir / "all_templates.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_static_files_txt(self) -> None:
        """Generate all_static_files.txt."""
        statics = self.auditor.extract_static_files()
        
        content = f"""# Static Files Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}

## Total Static Categories: {len(statics)}

"""
        
        total_files = 0
        for category in sorted(statics.keys()):
            files = statics[category]
            total_files += len(files)
            content += f"\n### {category}/\n"
            for file in files:
                content += f"   - {file}\n"
        
        content += f"\n**Total Static Files: {total_files}**\n"
        
        output_file = self.output_dir / "all_static_files.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_harvesters_txt(self) -> None:
        """Generate harvesters reference."""
        harvesters = self.auditor.extract_harvesters()
        
        content = f"""# Harvesters Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}

## Harvester Architecture

### Base Classes
"""
        
        for base in harvesters['base']:
            content += f"   - {base}\n"
        
        content += f"\n### Implementations\n"
        for impl in harvesters['implementations']:
            content += f"   - {impl}\n"
        
        content += f"\n### Utilities & Supporting\n"
        for util in harvesters['utilities']:
            content += f"   - {util}\n"
        
        output_file = self.output_dir / "harvesters_structure.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_services_txt(self) -> None:
        """Generate services reference."""
        services = self.auditor.extract_services()
        
        content = f"""# Services Audit
Generated: {datetime.now().isoformat()}
Project: {self.config.project_root.name}

## Total Service Modules: {len(services)}

"""
        
        for i, service in enumerate(services, 1):
            content += f"{i}. {service}\n"
        
        output_file = self.output_dir / "services_structure.txt"
        output_file.write_text(content, encoding='utf-8')
        print(f"✓ Generated: {output_file.name}")
    
    def generate_all(self) -> None:
        """Generate all audit documentation files."""
        print(f"\n{'='*60}")
        print(f"Generating Audit Documentation")
        print(f"Project: {self.config.project_root.name}")
        print(f"App: {self.config.django_app}")
        print(f"Output: {self.output_dir}")
        print(f"{'='*60}\n")
        
        self.generate_migrations_txt()
        self.generate_models_txt()
        self.generate_views_txt()
        self.generate_urls_txt()
        self.generate_management_commands_txt()
        self.generate_celery_tasks_txt()
        self.generate_templates_txt()
        self.generate_static_files_txt()
        self.generate_harvesters_txt()
        self.generate_services_txt()
        
        print(f"\n{'='*60}")
        print(f"✓ Audit documentation generation complete!")
        print(f"{'='*60}\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate audit documentation for Django projects."
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path(__file__).parent.parent,
        help='Path to Django project root (default: parent of scripts/)'
    )
    parser.add_argument(
        '--app',
        type=str,
        default='resources',
        help='Django app name to audit (default: resources)'
    )
    
    args = parser.parse_args()
    
    config = AuditConfig(
        project_root=args.project_root,
        django_app=args.app
    )
    
    auditor = DjangoProjectAuditor(config)
    generator = AuditDocumentGenerator(config, auditor)
    generator.generate_all()


if __name__ == '__main__':
    main()
