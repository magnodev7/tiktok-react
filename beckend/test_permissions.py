#!/usr/bin/env python3
"""
Script para testar permissões de escrita
"""

import os
import json
from pathlib import Path

def test_permissions():
    """Testa permissões de escrita nos diretórios"""
    print("🧪 Testando permissões de escrita...")
    
    # Diretórios para testar
    test_dirs = [
        Path("/app/users"),
        Path("/app/state"),
        Path("./users"),
        Path("./state")
    ]
    
    for test_dir in test_dirs:
        print(f"\n📁 Testando: {test_dir}")
        
        try:
            # Cria diretório se não existir
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # Testa escrita
            test_file = test_dir / "test_permissions.json"
            test_data = {"test": "permissions", "timestamp": "2024-01-01"}
            
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
            
            # Testa leitura
            with open(test_file, 'r') as f:
                data = json.load(f)
            
            # Remove arquivo de teste
            test_file.unlink()
            
            print(f"✅ {test_dir} - OK (leitura/escrita funcionando)")
            
        except PermissionError as e:
            print(f"❌ {test_dir} - Erro de permissão: {e}")
        except Exception as e:
            print(f"⚠️  {test_dir} - Erro: {e}")

if __name__ == "__main__":
    test_permissions()
