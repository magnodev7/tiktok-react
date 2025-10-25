#!/usr/bin/env python3
"""
Script para testar Selenium com Chrome local
"""
import sys
sys.path.insert(0, 'src')

from driver import build_driver

def test_selenium():
    """Testa se o Selenium consegue abrir o Chrome local"""
    print("🔧 Testando Selenium com Chrome local...")

    try:
        driver = build_driver()
        print("✅ Driver criado com sucesso!")

        # Testa navegação básica
        driver.get("https://www.google.com")
        print(f"✅ Navegação OK! Título: {driver.title}")

        # Fecha o driver
        driver.quit()
        print("✅ Teste concluído com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_selenium()
    sys.exit(0 if success else 1)
