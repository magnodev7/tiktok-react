#!/usr/bin/env python3
"""
Script de teste para o sistema de Analytics

Demonstra como usar a classe VideoAnalytics programaticamente
"""

from src.analytics import VideoAnalytics

def main():
    print("=" * 60)
    print("🔬 TESTE DO SISTEMA DE ANALYTICS")
    print("=" * 60)
    print()

    # Inicializa analytics
    analytics = VideoAnalytics(base_video_dir="./videos")

    # 1. Relatório resumido completo
    print("📊 RELATÓRIO RESUMIDO (últimos 30 dias)")
    print("-" * 60)
    report = analytics.generate_summary_report(account=None, days_back=30)

    print(f"✅ Total de vídeos: {report['overview']['total_videos']}")
    print(f"✅ Postados: {report['overview']['posted']}")
    print(f"❌ Falhas: {report['overview']['failed']}")
    print(f"⏳ Pendentes: {report['overview']['pending']}")
    print(f"📈 Taxa de sucesso: {report['overview']['success_rate']}%")
    print()

    # 2. Performance por modelo de IA
    print("🤖 PERFORMANCE POR MODELO DE IA")
    print("-" * 60)
    ai_stats = analytics.analyze_ai_performance(account=None, days_back=30)

    if ai_stats:
        for model, stats in sorted(ai_stats.items(), key=lambda x: x[1].total_videos, reverse=True):
            print(f"\n  🔹 {model}")
            print(f"     Vídeos: {stats.total_videos}")
            print(f"     Sucesso: {stats.success_rate}% ({stats.posted}/{stats.total_videos})")
            print(f"     Custo: ${stats.estimated_cost}")
            if stats.common_errors:
                print(f"     Erros: {stats.common_errors[0]}")
    else:
        print("  ℹ️  Nenhum vídeo gerado por IA encontrado")
    print()

    # 3. Performance por workflow N8N
    print("🔄 PERFORMANCE POR WORKFLOW N8N")
    print("-" * 60)
    workflow_stats = analytics.analyze_workflow_performance(account=None, days_back=30)

    if workflow_stats:
        for wf_id, stats in sorted(workflow_stats.items(), key=lambda x: x[1].total_videos, reverse=True):
            print(f"\n  🔹 {wf_id}")
            print(f"     Vídeos: {stats.total_videos}")
            print(f"     Sucesso: {stats.success_rate}% ({stats.posted}/{stats.total_videos})")
            print(f"     IA: {stats.ai_model_used or 'N/A'}")
            print(f"     Último: {stats.last_video_at or 'N/A'}")
    else:
        print("  ℹ️  Nenhum workflow N8N encontrado")
    print()

    # 4. Performance por origem
    print("📍 PERFORMANCE POR ORIGEM")
    print("-" * 60)
    source_stats = analytics.analyze_by_source(account=None, days_back=30)

    if source_stats:
        for source, stats in sorted(source_stats.items(), key=lambda x: x[1].total_videos, reverse=True):
            print(f"\n  🔹 {source}")
            print(f"     Vídeos: {stats.total_videos}")
            print(f"     Sucesso: {stats.success_rate}% ({stats.posted}/{stats.total_videos})")
    else:
        print("  ℹ️  Nenhuma origem encontrada")
    print()

    # 5. Alertas automáticos
    print("🚨 ALERTAS AUTOMÁTICOS")
    print("-" * 60)
    alerts = analytics.detect_issues(account=None)

    if alerts:
        for i, alert in enumerate(alerts, 1):
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(alert["severity"], "⚪")
            print(f"\n  {severity_icon} [{alert['severity'].upper()}] {alert['message']}")
            print(f"     Tipo: {alert['type']}")
            print(f"     💡 Recomendação: {alert['recommendation']}")
    else:
        print("  ✅ Nenhum problema detectado!")
    print()

    # 6. Custos estimados
    print("💰 CUSTOS ESTIMADOS DE IA")
    print("-" * 60)
    print(f"  Total: ${report['costs']['total_ai_cost_usd']:.2f} USD")
    print(f"  Por vídeo: ${report['costs']['cost_per_video']:.4f} USD")
    print(f"\n  Por modelo:")
    for model, cost in report['costs']['by_model'].items():
        print(f"    • {model}: ${cost:.2f}")
    print()

    print("=" * 60)
    print("✅ TESTE CONCLUÍDO")
    print("=" * 60)


if __name__ == "__main__":
    main()
