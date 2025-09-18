#!/usr/bin/env python3
"""
FINAL PRODUCTION READINESS VALIDATION
Comprehensive testing and certification for production deployment
"""

import os
import time
import requests
import json
from typing import Dict, List, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionValidator:
    """Comprehensive production readiness validator"""
    
    def __init__(self, backend_url: str = "http://localhost:8000", frontend_url: str = "http://localhost:5173"):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.test_results = []
        
    def test_backend_health(self) -> Dict[str, Any]:
        """Test backend health and OCR system status"""
        print("\n🔍 TESTING BACKEND HEALTH")
        print("-" * 50)
        
        try:
            # Test basic endpoints
            response = requests.get(f"{self.backend_url}/api/batches", timeout=10)
            backend_responsive = response.status_code == 200
            
            print(f"✅ Backend API: {'RESPONSIVE' if backend_responsive else 'NOT RESPONSIVE'}")
            
            # Test file upload capability
            test_file_path = "/Users/yapi/Adi/App-Dev/doc-scan-ai/backend/uploads"
            
            # Find a test PDF
            test_pdf = None
            for subdir in os.listdir(test_file_path):
                subdir_path = os.path.join(test_file_path, subdir)
                if os.path.isdir(subdir_path):
                    for file in os.listdir(subdir_path):
                        if file.lower().endswith('.pdf'):
                            test_pdf = os.path.join(subdir_path, file)
                            break
                    if test_pdf:
                        break
            
            upload_test = False
            ocr_performance = {}
            
            if test_pdf and os.path.exists(test_pdf):
                try:
                    print(f"📄 Testing with: {os.path.basename(test_pdf)}")
                    
                    start_time = time.time()
                    
                    with open(test_pdf, 'rb') as f:
                        files = {'file': (os.path.basename(test_pdf), f, 'application/pdf')}
                        upload_response = requests.post(
                            f"{self.backend_url}/api/upload", 
                            files=files, 
                            timeout=30
                        )
                    
                    upload_time = time.time() - start_time
                    upload_test = upload_response.status_code == 200
                    
                    if upload_test:
                        batch_data = upload_response.json()
                        batch_id = batch_data.get('batch_id')
                        
                        # Wait for processing
                        time.sleep(2)
                        
                        # Get results
                        results_response = requests.get(
                            f"{self.backend_url}/api/batches/{batch_id}/results",
                            timeout=10
                        )
                        
                        if results_response.status_code == 200:
                            results = results_response.json()
                            
                            ocr_performance = {
                                'upload_time': upload_time,
                                'processing_successful': len(results.get('results', [])) > 0,
                                'total_documents': len(results.get('results', [])),
                                'successful_documents': len([r for r in results.get('results', []) if r.get('status') == 'completed']),
                                'total_characters': sum([len(r.get('extracted_text', '')) for r in results.get('results', [])]),
                                'avg_confidence': sum([r.get('confidence', 0) for r in results.get('results', [])]) / max(len(results.get('results', [])), 1)
                            }
                            
                            print(f"⏱️ Upload Time: {upload_time:.2f}s")
                            print(f"📊 OCR Success: {ocr_performance['successful_documents']}/{ocr_performance['total_documents']}")
                            print(f"📏 Characters Extracted: {ocr_performance['total_characters']:,}")
                            print(f"🎯 Average Confidence: {ocr_performance['avg_confidence']:.1f}%")
                
                except Exception as e:
                    print(f"❌ Upload test failed: {e}")
            
            print(f"✅ File Upload: {'WORKING' if upload_test else 'FAILED'}")
            
            return {
                'backend_responsive': backend_responsive,
                'upload_working': upload_test,
                'ocr_performance': ocr_performance,
                'overall_health': backend_responsive and upload_test
            }
            
        except Exception as e:
            print(f"❌ Backend health test failed: {e}")
            return {
                'backend_responsive': False,
                'upload_working': False,
                'ocr_performance': {},
                'overall_health': False
            }
    
    def test_frontend_connectivity(self) -> Dict[str, Any]:
        """Test frontend connectivity and responsiveness"""
        print("\n🌐 TESTING FRONTEND CONNECTIVITY")
        print("-" * 50)
        
        try:
            response = requests.get(self.frontend_url, timeout=10)
            frontend_responsive = response.status_code == 200
            
            print(f"✅ Frontend: {'RESPONSIVE' if frontend_responsive else 'NOT RESPONSIVE'}")
            
            return {
                'frontend_responsive': frontend_responsive,
                'status_code': response.status_code
            }
            
        except Exception as e:
            print(f"❌ Frontend connectivity test failed: {e}")
            return {
                'frontend_responsive': False,
                'status_code': 0
            }
    
    def test_system_performance(self) -> Dict[str, Any]:
        """Test overall system performance metrics"""
        print("\n⚡ TESTING SYSTEM PERFORMANCE")
        print("-" * 50)
        
        # Import production OCR for direct testing
        try:
            from production_ocr import ProductionOCRProcessor
            processor = ProductionOCRProcessor(max_workers=1, memory_limit_mb=256)
            
            # Health check
            health = processor.health_check()
            
            print(f"🏥 OCR System Health: {health['status'].upper()}")
            print(f"🔧 Available Engines: {', '.join(health['ocr_engines_available'])}")
            print(f"💾 Memory Usage: {health['memory_usage_mb']:.1f}MB")
            print(f"💿 Disk Space: {'OK' if health['disk_space_available'] else 'LOW'}")
            
            # Performance test
            test_files = []
            uploads_dir = "/Users/yapi/Adi/App-Dev/doc-scan-ai/backend/uploads"
            
            for subdir in os.listdir(uploads_dir):
                subdir_path = os.path.join(uploads_dir, subdir)
                if os.path.isdir(subdir_path):
                    for file in os.listdir(subdir_path):
                        if file.lower().endswith('.pdf'):
                            test_files.append(os.path.join(subdir_path, file))
                            if len(test_files) >= 5:  # Test with 5 files
                                break
                    if len(test_files) >= 5:
                        break
            
            if test_files:
                print(f"📄 Performance testing with {len(test_files)} documents...")
                
                start_time = time.time()
                results = processor.process_batch(test_files)
                total_time = time.time() - start_time
                
                successful = [r for r in results if r['success']]
                stats = processor.get_statistics()
                
                performance_metrics = {
                    'total_files': len(test_files),
                    'successful_files': len(successful),
                    'success_rate': len(successful) / len(test_files) * 100,
                    'total_processing_time': total_time,
                    'avg_time_per_file': total_time / len(test_files),
                    'total_characters': sum([r.get('text_length', 0) for r in successful]),
                    'avg_confidence': sum([r.get('confidence', 0) for r in successful]) / max(len(successful), 1),
                    'memory_efficient': health['memory_usage_mb'] < 2000,  # Under 2GB
                    'speed_efficient': total_time / len(test_files) < 1.0  # Under 1s per file
                }
                
                print(f"📈 Success Rate: {performance_metrics['success_rate']:.1f}%")
                print(f"⚡ Avg Time/File: {performance_metrics['avg_time_per_file']:.2f}s")
                print(f"📊 Avg Confidence: {performance_metrics['avg_confidence']:.1f}%")
                print(f"💾 Memory Efficient: {'YES' if performance_metrics['memory_efficient'] else 'NO'}")
                print(f"⚡ Speed Efficient: {'YES' if performance_metrics['speed_efficient'] else 'NO'}")
                
                return {
                    'ocr_health': health,
                    'performance_metrics': performance_metrics,
                    'system_ready': (
                        performance_metrics['success_rate'] >= 90 and
                        performance_metrics['avg_confidence'] >= 90 and
                        performance_metrics['memory_efficient'] and
                        performance_metrics['speed_efficient']
                    )
                }
            else:
                print("❌ No test files found")
                return {'system_ready': False}
                
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            return {'system_ready': False}
    
    def generate_production_report(self, backend_health: Dict, frontend_health: Dict, performance: Dict) -> Dict[str, Any]:
        """Generate comprehensive production readiness report"""
        print("\n" + "=" * 80)
        print("🏆 PRODUCTION READINESS REPORT")
        print("=" * 80)
        
        # Calculate scores
        backend_score = 0
        if backend_health.get('backend_responsive'): backend_score += 25
        if backend_health.get('upload_working'): backend_score += 25
        if backend_health.get('ocr_performance', {}).get('processing_successful'): backend_score += 25
        if backend_health.get('ocr_performance', {}).get('avg_confidence', 0) >= 90: backend_score += 25
        
        frontend_score = 100 if frontend_health.get('frontend_responsive') else 0
        
        performance_score = 0
        if performance.get('performance_metrics', {}).get('success_rate', 0) >= 95: performance_score += 30
        if performance.get('performance_metrics', {}).get('avg_confidence', 0) >= 90: performance_score += 30
        if performance.get('performance_metrics', {}).get('memory_efficient'): performance_score += 20
        if performance.get('performance_metrics', {}).get('speed_efficient'): performance_score += 20
        
        overall_score = (backend_score + frontend_score + performance_score) / 3
        
        # Deployment readiness assessment
        deployment_ready = (
            backend_score >= 85 and
            frontend_score >= 85 and
            performance_score >= 85 and
            overall_score >= 90
        )
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'scores': {
                'backend': backend_score,
                'frontend': frontend_score,
                'performance': performance_score,
                'overall': overall_score
            },
            'readiness': {
                'deployment_ready': deployment_ready,
                'recommendation': self._get_deployment_recommendation(overall_score),
                'critical_issues': self._identify_critical_issues(backend_health, frontend_health, performance)
            },
            'technical_summary': {
                'ocr_accuracy': performance.get('performance_metrics', {}).get('avg_confidence', 0),
                'processing_speed': performance.get('performance_metrics', {}).get('avg_time_per_file', 0),
                'system_stability': backend_health.get('overall_health', False),
                'frontend_responsive': frontend_health.get('frontend_responsive', False)
            }
        }
        
        # Display report
        print(f"📊 SYSTEM SCORES:")
        print(f"   Backend System: {backend_score:.1f}/100")
        print(f"   Frontend System: {frontend_score:.1f}/100")
        print(f"   Performance: {performance_score:.1f}/100")
        print(f"   Overall Score: {overall_score:.1f}/100")
        
        print(f"\n🎯 TECHNICAL METRICS:")
        print(f"   OCR Accuracy: {report['technical_summary']['ocr_accuracy']:.1f}%")
        print(f"   Processing Speed: {report['technical_summary']['processing_speed']:.2f}s/file")
        print(f"   System Stability: {'STABLE' if report['technical_summary']['system_stability'] else 'UNSTABLE'}")
        print(f"   Frontend Status: {'RESPONSIVE' if report['technical_summary']['frontend_responsive'] else 'ISSUES'}")
        
        print(f"\n🚀 DEPLOYMENT STATUS:")
        status_emoji = "✅" if deployment_ready else "⚠️"
        print(f"   {status_emoji} Ready for Production: {'YES' if deployment_ready else 'NO'}")
        print(f"   📋 Recommendation: {report['readiness']['recommendation']}")
        
        if report['readiness']['critical_issues']:
            print(f"\n❗ CRITICAL ISSUES TO ADDRESS:")
            for issue in report['readiness']['critical_issues']:
                print(f"   • {issue}")
        
        # Final certification
        if deployment_ready:
            print(f"\n🏆 PRODUCTION CERTIFICATION")
            print(f"   ✅ System CERTIFIED for production deployment")
            print(f"   ✅ All critical tests PASSED")
            print(f"   ✅ Performance meets enterprise standards")
            print(f"   🚀 READY TO DEPLOY!")
        else:
            print(f"\n⚠️  PRODUCTION CERTIFICATION PENDING")
            print(f"   ❌ Address critical issues before deployment")
            print(f"   📋 Follow recommendations for improvements")
        
        return report
    
    def _get_deployment_recommendation(self, score: float) -> str:
        """Get deployment recommendation based on score"""
        if score >= 95:
            return "IMMEDIATE DEPLOYMENT APPROVED - Excellent performance"
        elif score >= 90:
            return "DEPLOYMENT APPROVED - Good performance, monitor in production"
        elif score >= 80:
            return "CONDITIONAL DEPLOYMENT - Address minor issues first"
        elif score >= 70:
            return "STAGED DEPLOYMENT - Limited rollout recommended"
        else:
            return "DEPLOYMENT NOT RECOMMENDED - Major issues require resolution"
    
    def _identify_critical_issues(self, backend: Dict, frontend: Dict, performance: Dict) -> List[str]:
        """Identify critical issues that block production deployment"""
        issues = []
        
        if not backend.get('backend_responsive'):
            issues.append("Backend API not responsive")
        
        if not backend.get('upload_working'):
            issues.append("File upload functionality broken")
        
        if not frontend.get('frontend_responsive'):
            issues.append("Frontend not accessible")
        
        perf_metrics = performance.get('performance_metrics', {})
        if perf_metrics.get('success_rate', 0) < 90:
            issues.append(f"OCR success rate too low: {perf_metrics.get('success_rate', 0):.1f}%")
        
        if perf_metrics.get('avg_confidence', 0) < 85:
            issues.append(f"OCR confidence too low: {perf_metrics.get('avg_confidence', 0):.1f}%")
        
        if not perf_metrics.get('memory_efficient'):
            issues.append("Memory usage too high for production")
        
        if not perf_metrics.get('speed_efficient'):
            issues.append("Processing speed too slow for production load")
        
        return issues
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete production validation suite"""
        print("🚀 STARTING PRODUCTION READINESS VALIDATION")
        print("=" * 80)
        
        # Test backend
        backend_health = self.test_backend_health()
        
        # Test frontend
        frontend_health = self.test_frontend_connectivity()
        
        # Test performance
        performance = self.test_system_performance()
        
        # Generate final report
        report = self.generate_production_report(backend_health, frontend_health, performance)
        
        return {
            'backend_health': backend_health,
            'frontend_health': frontend_health,
            'performance': performance,
            'final_report': report
        }

def main():
    """Main validation function"""
    validator = ProductionValidator()
    
    try:
        results = validator.run_full_validation()
        
        # Save report to file
        report_file = f"production_validation_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return results['final_report']['readiness']['deployment_ready']
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)