"""
Bias detection service for fair AI screening
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from uuid import uuid4
from loguru import logger
from sklearn.metrics import confusion_matrix

from ..models.schemas import (
    BiasAnalysisResponse, BiasMetricResult, AttributeAnalysis
)
from ..models.enums import BiasMetric, Gender
from ..config import settings
from ..core.exceptions import BiasDetectionError

class BiasDetector:
    """
    Detect bias in resume screening outcomes
    Implements multiple fairness metrics
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.protected_attributes = settings.bias_protected_attributes
        self.threshold = settings.bias_threshold
    
    async def analyze_bias(
        self,
        attribute: str,
        sample_size: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AttributeAnalysis:
        """
        Analyze bias for a specific protected attribute
        """
        if attribute not in self.protected_attributes:
            raise BiasDetectionError(f"Unknown attribute: {attribute}. Available: {self.protected_attributes}")
        
        # Get data
        data = await self._get_screening_data(attribute, sample_size, start_date, end_date)
        
        if len(data) < 50:
            raise BiasDetectionError(f"Insufficient data for {attribute}. Need at least 50 samples, got {len(data)}")
        
        # Calculate metrics
        metrics = []
        
        # Statistical Parity
        stat_parity = await self._calculate_statistical_parity(data, attribute)
        metrics.append(stat_parity)
        
        # Demographic Parity
        demo_parity = await self._calculate_demographic_parity(data, attribute)
        metrics.append(demo_parity)
        
        # Equal Opportunity
        equal_opp = await self._calculate_equal_opportunity(data, attribute)
        metrics.append(equal_opp)
        
        # Disparate Impact
        disp_impact = await self._calculate_disparate_impact(data, attribute)
        metrics.append(disp_impact)
        
        # Calculate overall bias score (average of metric deviations)
        bias_scores = [m.value for m in metrics]
        overall_bias = np.mean(bias_scores)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(metrics, overall_bias)
        
        # Get distribution
        distribution = self._get_distribution(data, attribute)
        
        return AttributeAnalysis(
            attribute=attribute,
            metrics=metrics,
            overall_bias_score=overall_bias,
            recommendation=recommendation,
            sample_size=len(data),
            distribution=distribution
        )
    
    async def _get_screening_data(
        self,
        attribute: str,
        sample_size: Optional[int],
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> pd.DataFrame:
        """Get screening data from database"""
        from ..models.database import MatchResult, Resume
        
        query = self.db.query(MatchResult, Resume).join(
            Resume, MatchResult.resume_id == Resume.id
        )
        
        # Apply filters
        if start_date:
            query = query.filter(MatchResult.created_at >= start_date)
        if end_date:
            query = query.filter(MatchResult.created_at <= end_date)
        
        # Get data
        results = query.all()
        
        # Convert to DataFrame
        data = []
        for match, resume in results:
            # Get protected attribute value
            attr_value = self._get_attribute_value(resume, attribute)
            
            if attr_value and attr_value != "unknown":
                data.append({
                    'score': match.overall_score,
                    'attribute': attr_value,
                    'is_selected': match.overall_score >= settings.similarity_threshold,
                    'resume_id': resume.id,
                    'match_id': match.id
                })
        
        df = pd.DataFrame(data)
        
        # Sample if needed
        if sample_size and len(df) > sample_size:
            df = df.sample(n=sample_size, random_state=42)
        
        return df
    
    def _get_attribute_value(self, resume, attribute: str) -> Optional[str]:
        """Get protected attribute value from resume"""
        if attribute == "gender":
            return getattr(resume, 'inferred_gender', None)
        elif attribute == "age":
            age_group = getattr(resume, 'inferred_age_group', None)
            return age_group
        elif attribute == "ethnicity":
            return getattr(resume, 'inferred_ethnicity_hint', None)
        return None
    
    async def _calculate_statistical_parity(self, data: pd.DataFrame, attribute: str) -> BiasMetricResult:
        """
        Statistical parity: Is selection rate equal across groups?
        Ratio of selection rates between groups
        """
        groups = data['attribute'].unique()
        
        if len(groups) < 2:
            return BiasMetricResult(
                metric_name="Statistical Parity",
                value=1.0,
                interpretation="Only one group found",
                is_biased=False,
                threshold=self.threshold
            )
        
        # Calculate selection rates
        selection_rates = {}
        for group in groups:
            group_data = data[data['attribute'] == group]
            selection_rate = group_data['is_selected'].mean()
            selection_rates[group] = selection_rate
        
        # Find min and max rates
        max_rate = max(selection_rates.values())
        min_rate = min(selection_rates.values())
        
        # Calculate ratio (avoid division by zero)
        if min_rate == 0:
            ratio = 1.0 if max_rate == 0 else float('inf')
        else:
            ratio = max_rate / min_rate
        
        # Determine if biased (ratio > threshold or < 1/threshold)
        is_biased = ratio > self.threshold or ratio < (1 / self.threshold)
        
        interpretation = self._interpret_statistical_parity(selection_rates, ratio)
        
        return BiasMetricResult(
            metric_name="Statistical Parity",
            value=min(ratio, 1/ratio) if ratio != float('inf') else 0,
            interpretation=interpretation,
            is_biased=is_biased,
            threshold=self.threshold
        )
    
    async def _calculate_demographic_parity(self, data: pd.DataFrame, attribute: str) -> BiasMetricResult:
        """
        Demographic parity: Difference in positive outcomes between groups
        """
        groups = data['attribute'].unique()
        
        if len(groups) < 2:
            return BiasMetricResult(
                metric_name="Demographic Parity",
                value=0.0,
                interpretation="Only one group found",
                is_biased=False,
                threshold=self.threshold
            )
        
        # Calculate differences
        differences = []
        group_scores = {}
        
        for group in groups:
            group_data = data[data['attribute'] == group]
            positive_rate = group_data['is_selected'].mean()
            group_scores[group] = positive_rate
        
        # Calculate pairwise differences
        group_list = list(groups)
        for i in range(len(group_list)):
            for j in range(i+1, len(group_list)):
                diff = abs(group_scores[group_list[i]] - group_scores[group_list[j]])
                differences.append(diff)
        
        max_difference = max(differences) if differences else 0
        is_biased = max_difference > self.threshold
        
        interpretation = self._interpret_demographic_parity(group_scores, max_difference)
        
        return BiasMetricResult(
            metric_name="Demographic Parity",
            value=max_difference,
            interpretation=interpretation,
            is_biased=is_biased,
            threshold=self.threshold
        )
    
    async def _calculate_equal_opportunity(self, data: pd.DataFrame, attribute: str) -> BiasMetricResult:
        """
        Equal opportunity: Equal true positive rates across groups
        """
        groups = data['attribute'].unique()
        
        if len(groups) < 2:
            return BiasMetricResult(
                metric_name="Equal Opportunity",
                value=0.0,
                interpretation="Only one group found",
                is_biased=False,
                threshold=self.threshold
            )
        
        # Need a notion of "qualified" - using score > 0.7 as proxy
        qualified_threshold = 0.7
        
        tpr_by_group = {}
        
        for group in groups:
            group_data = data[data['attribute'] == group]
            
            # Qualified candidates (based on score)
            qualified = group_data[group_data['score'] >= qualified_threshold]
            
            if len(qualified) > 0:
                # True positives: qualified AND selected
                true_positives = qualified[qualified['is_selected'] == True].shape[0]
                tpr = true_positives / len(qualified)
            else:
                tpr = 0
            
            tpr_by_group[group] = tpr
        
        # Find max difference in TPR
        tpr_values = list(tpr_by_group.values())
        max_diff = max(tpr_values) - min(tpr_values)
        is_biased = max_diff > self.threshold
        
        interpretation = self._interpret_equal_opportunity(tpr_by_group, max_diff)
        
        return BiasMetricResult(
            metric_name="Equal Opportunity",
            value=max_diff,
            interpretation=interpretation,
            is_biased=is_biased,
            threshold=self.threshold
        )
    
    async def _calculate_disparate_impact(self, data: pd.DataFrame, attribute: str) -> BiasMetricResult:
        """
        Disparate impact: 80% rule (selection rate of minority group >= 80% of majority)
        """
        groups = data['attribute'].unique()
        
        if len(groups) < 2:
            return BiasMetricResult(
                metric_name="Disparate Impact",
                value=1.0,
                interpretation="Only one group found",
                is_biased=False,
                threshold=0.8
            )
        
        # Calculate selection rates
        selection_rates = {}
        for group in groups:
            group_data = data[data['attribute'] == group]
            selection_rates[group] = group_data['is_selected'].mean()
        
        # Find group with highest selection rate (reference)
        reference_group = max(selection_rates, key=selection_rates.get)
        reference_rate = selection_rates[reference_group]
        
        # Calculate impact ratios
        impact_ratios = []
        for group, rate in selection_rates.items():
            if group != reference_group and reference_rate > 0:
                ratio = rate / reference_rate
                impact_ratios.append(ratio)
        
        min_impact = min(impact_ratios) if impact_ratios else 1.0
        
        # 80% rule: impact ratio should be >= 0.8
        is_biased = min_impact < 0.8
        
        interpretation = self._interpret_disparate_impact(selection_rates, min_impact)
        
        return BiasMetricResult(
            metric_name="Disparate Impact",
            value=min_impact,
            interpretation=interpretation,
            is_biased=is_biased,
            threshold=0.8
        )
    
    def _interpret_statistical_parity(self, rates: Dict, ratio: float) -> str:
        """Generate interpretation for statistical parity"""
        if ratio == float('inf'):
            return "One group has zero selection rate while another has positive rate - severe bias detected"
        elif ratio > self.threshold:
            return f"Selection rates vary significantly (max ratio: {ratio:.2f}). Highest rate group has {ratio:.1f}x higher selection rate than lowest group"
        else:
            return f"Selection rates are relatively balanced across groups (max ratio: {ratio:.2f})"
    
    def _interpret_demographic_parity(self, scores: Dict, max_diff: float) -> str:
        """Generate interpretation for demographic parity"""
        if max_diff > self.threshold:
            return f"Large difference in positive outcomes ({max_diff:.2f}). Highest rate group has {max_diff*100:.1f}% higher selection rate"
        else:
            return f"Positive outcome rates are balanced (max difference: {max_diff:.2f})"
    
    def _interpret_equal_opportunity(self, tprs: Dict, max_diff: float) -> str:
        """Generate interpretation for equal opportunity"""
        if max_diff > self.threshold:
            return f"Unequal true positive rates across groups (max difference: {max_diff:.2f}). Qualified candidates from some groups have lower chance of being selected"
        else:
            return f"True positive rates are balanced across groups (max difference: {max_diff:.2f})"
    
    def _interpret_disparate_impact(self, rates: Dict, min_impact: float) -> str:
        """Generate interpretation for disparate impact"""
        min_group = min(rates, key=rates.get)
        max_group = max(rates, key=rates.get)
        
        if min_impact < 0.8:
            return f"Disparate impact detected. {min_group} group has only {min_impact*100:.1f}% of the selection rate of {max_group} group (80% rule violated)"
        else:
            return f"No disparate impact. Lowest selection rate is {min_impact*100:.1f}% of highest (within 80% rule)"
    
    def _get_distribution(self, data: pd.DataFrame, attribute: str) -> Dict[str, int]:
        """Get distribution of attribute values"""
        distribution = data['attribute'].value_counts().to_dict()
        
        # Convert to regular dict with string keys
        return {str(k): int(v) for k, v in distribution.items()}
    
    def _generate_recommendation(self, metrics: List[BiasMetricResult], overall_bias: float) -> str:
        """Generate recommendation based on bias analysis"""
        biased_metrics = [m for m in metrics if m.is_biased]
        
        if not biased_metrics:
            return "No significant bias detected. The screening process appears to be fair across all measured metrics."
        
        if len(biased_metrics) >= 3:
            return "CRITICAL: Multiple bias metrics indicate unfair screening. Review your matching algorithm and consider removing protected attributes from the screening process."
        
        elif len(biased_metrics) >= 2:
            return "WARNING: Bias detected in multiple areas. Consider recalibrating your similarity thresholds and reviewing feature importance."
        
        else:
            return f"MINOR BIAS: {biased_metrics[0].metric_name} shows bias. Focus on improving this specific metric first."
    
    async def generate_full_report(
        self,
        sample_size: Optional[int] = None,
        lookback_days: int = 90
    ) -> BiasAnalysisResponse:
        """Generate complete bias report for all protected attributes"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        analyses = []
        recommendations = []
        
        for attribute in self.protected_attributes:
            try:
                analysis = await self.analyze_bias(
                    attribute=attribute,
                    sample_size=sample_size,
                    start_date=start_date,
                    end_date=end_date
                )
                analyses.append(analysis)
                
                if analysis.overall_bias_score > 0.7:
                    recommendations.append(f"Address bias in {attribute}: {analysis.recommendation}")
                    
            except Exception as e:
                logger.error(f"Failed to analyze {attribute}: {str(e)}")
        
        # Determine overall risk level
        high_bias_count = sum(1 for a in analyses if a.overall_bias_score > 0.7)
        
        if high_bias_count >= 2:
            overall_risk = "High"
        elif high_bias_count == 1:
            overall_risk = "Medium"
        else:
            overall_risk = "Low"
        
        return BiasAnalysisResponse(
            analysis_id=uuid4(),
            timestamp=datetime.now(),
            analyses=analyses,
            overall_risk_level=overall_risk,
            recommendations=recommendations
        )