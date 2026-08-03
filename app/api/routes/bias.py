"""
Bias detection and fairness analysis endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional
from datetime import datetime
from loguru import logger

from ...models.schemas import BiasAnalysisRequest, BiasAnalysisResponse
from ...config import settings
from ...dependencies import get_db
from ...services.bias_detector import BiasDetector

router = APIRouter(prefix="/bias", tags=["Bias Detection"])

@router.post("/analyze", response_model=BiasAnalysisResponse)
async def analyze_bias(
    request: BiasAnalysisRequest,
    db=Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Analyze bias for a specific protected attribute
    """
    detector = BiasDetector(db)
    
    try:
        analysis = await detector.analyze_bias(
            attribute=request.attribute,
            sample_size=request.sample_size or settings.bias_sample_size,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        return BiasAnalysisResponse(
            analysis_id=analysis.analysis_id,
            timestamp=analysis.timestamp,
            analyses=[analysis],
            overall_risk_level=analysis.overall_risk_level,
            recommendations=analysis.recommendations
        )
        
    except Exception as e:
        logger.error(f"Bias analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bias analysis failed: {str(e)}")

@router.get("/report", response_model=BiasAnalysisResponse)
async def generate_bias_report(
    lookback_days: int = 90,
    sample_size: Optional[int] = None,
    db=Depends(get_db)
):
    """
    Generate comprehensive bias report for all protected attributes
    """
    detector = BiasDetector(db)
    
    try:
        report = await detector.generate_full_report(
            sample_size=sample_size or settings.bias_sample_size,
            lookback_days=lookback_days
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Bias report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/metrics")
async def get_available_metrics():
    """
    Get list of available bias metrics
    """
    return {
        "metrics": [
            {
                "name": "statistical_parity",
                "description": "Compares selection rates across groups",
                "threshold": settings.bias_threshold,
                "interpretation": "Ratio of selection rates. Values < 0.8 or > 1.25 indicate bias"
            },
            {
                "name": "demographic_parity",
                "description": "Difference in positive outcome rates",
                "threshold": settings.bias_threshold,
                "interpretation": "Absolute difference in selection rates"
            },
            {
                "name": "equal_opportunity",
                "description": "Equal true positive rates across groups",
                "threshold": settings.bias_threshold,
                "interpretation": "Difference in TPR between groups"
            },
            {
                "name": "disparate_impact",
                "description": "80% rule compliance",
                "threshold": 0.8,
                "interpretation": "Ratio of lowest to highest selection rate"
            }
        ],
        "protected_attributes": settings.bias_protected_attributes,
        "sample_size_recommendation": f"Minimum {settings.bias_sample_size} samples for reliable analysis"
    }

@router.post("/mitigate")
async def suggest_mitigations(
    attribute: str,
    db=Depends(get_db)
):
    """
    Get suggestions for mitigating detected bias
    """
    detector = BiasDetector(db)
    
    try:
        analysis = await detector.analyze_bias(attribute=attribute)
        
        mitigations = []
        
        # Generate specific mitigations based on metrics
        for metric in analysis.metrics:
            if metric.is_biased:
                if metric.metric_name == "Statistical Parity":
                    mitigations.append({
                        "action": "Calibrate selection thresholds",
                        "description": "Adjust similarity threshold differently for different groups based on score distributions",
                        "priority": "High"
                    })
                elif metric.metric_name == "Demographic Parity":
                    mitigations.append({
                        "action": "Review feature importance",
                        "description": "Check if certain features are correlating with protected attributes",
                        "priority": "Medium"
                    })
                elif metric.metric_name == "Disparate Impact":
                    mitigations.append({
                        "action": "Implement fairness constraints",
                        "description": "Add constraints to ensure selection rates stay within 80% rule",
                        "priority": "High"
                    })
        
        # General mitigations
        mitigations.append({
            "action": "Remove identifying information",
            "description": "Strip names, locations, and other potential bias indicators before processing",
            "priority": "Medium"
        })
        
        mitigations.append({
            "action": "Regular auditing",
            "description": f"Schedule weekly bias audits for {attribute}",
            "priority": "Low"
        })
        
        return {
            "attribute": attribute,
            "bias_score": analysis.overall_bias_score,
            "risk_level": "High" if analysis.overall_bias_score > 0.7 else "Medium" if analysis.overall_bias_score > 0.5 else "Low",
            "mitigations": mitigations,
            "recommendation": analysis.recommendation
        }
        
    except Exception as e:
        logger.error(f"Mitigation suggestions failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))