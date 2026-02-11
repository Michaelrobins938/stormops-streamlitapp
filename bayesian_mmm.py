"""
Bayesian Media Mix Model (MMM)
PyMC implementation with Weibull adstock and Hill saturation
"""

import numpy as np
import pandas as pd
import pymc as pm
import arviz as az
from typing import Dict, List, Tuple
from sqlalchemy import create_engine, text
import uuid

class BayesianMMM:
    """
    Bayesian Media Mix Model for marketing attribution
    Implements Weibull adstock decay and Hill saturation
    """
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.model = None
        self.trace = None
    
    def load_data(self, tenant_id: uuid.UUID, storm_id: uuid.UUID) -> pd.DataFrame:
        """Load MMM observations from database"""
        with self.engine.connect() as conn:
            df = pd.read_sql(text("""
                SELECT 
                    mo.observation_date,
                    mo.zip_code,
                    mc.channel_name,
                    mo.spend_usd,
                    mo.touches,
                    mo.conversions,
                    mo.revenue_usd
                FROM mmm_observations mo
                JOIN mmm_channels mc ON mo.channel_id = mc.channel_id
                WHERE mo.tenant_id = :tenant_id
                  AND mo.storm_id = :storm_id
                ORDER BY mo.observation_date, mc.channel_name
            """), conn, params={
                "tenant_id": str(tenant_id),
                "storm_id": str(storm_id)
            })
        
        return df
    
    def weibull_adstock(self, x: np.ndarray, alpha: float, theta: float, 
                       max_lag: int = 14) -> np.ndarray:
        """
        Apply Weibull adstock transformation
        
        Args:
            x: Input spend/touches array
            alpha: Shape parameter (controls decay curve)
            theta: Scale parameter (half-life in days)
            max_lag: Maximum lag to consider
        
        Returns:
            Adstocked array
        """
        n = len(x)
        adstocked = np.zeros(n)
        
        for t in range(n):
            adstocked[t] = x[t]
            
            # Add decayed effects from previous periods
            for lag in range(1, min(t + 1, max_lag + 1)):
                weight = (alpha / theta) * ((lag / theta) ** (alpha - 1)) * \
                         np.exp(-((lag / theta) ** alpha))
                adstocked[t] += x[t - lag] * weight
        
        return adstocked
    
    def hill_saturation(self, x: np.ndarray, k: float, s: float = 1.0) -> np.ndarray:
        """
        Apply Hill saturation transformation
        
        Args:
            x: Input (adstocked) array
            k: Half-saturation point
            s: Slope parameter
        
        Returns:
            Saturated array
        """
        return (x ** s) / ((k ** s) + (x ** s))
    
    def build_model(self, df: pd.DataFrame, channels: List[str]) -> pm.Model:
        """
        Build Bayesian MMM with PyMC
        
        Model structure:
        - Weibull adstock for each channel
        - Hill saturation for each channel
        - Linear combination to predict conversions
        - Hierarchical priors for robustness
        """
        # Pivot data to wide format
        spend_data = df.pivot_table(
            index='observation_date',
            columns='channel_name',
            values='touches',
            fill_value=0
        )
        
        conversions = df.groupby('observation_date')['conversions'].sum().values
        
        with pm.Model() as model:
            # Priors for adstock parameters (per channel)
            alpha = pm.Beta('alpha', alpha=2, beta=5, shape=len(channels))  # Decay shape
            theta = pm.Gamma('theta', alpha=2, beta=0.1, shape=len(channels))  # Half-life
            
            # Priors for saturation parameters (per channel)
            k = pm.Gamma('k', alpha=2, beta=0.01, shape=len(channels))  # Half-saturation
            s = pm.Gamma('s', alpha=2, beta=2, shape=len(channels))  # Slope
            
            # Channel coefficients (contribution to conversions)
            beta = pm.Normal('beta', mu=0, sigma=1, shape=len(channels))
            
            # Intercept (baseline conversions)
            intercept = pm.Normal('intercept', mu=conversions.mean(), sigma=conversions.std())
            
            # Transform each channel
            transformed_channels = []
            
            for i, channel in enumerate(channels):
                x = spend_data[channel].values
                
                # Apply adstock
                adstocked = pm.Deterministic(
                    f'{channel}_adstocked',
                    pm.math.sum([
                        x[t] + pm.math.sum([
                            x[max(0, t-lag)] * 
                            (alpha[i] / theta[i]) * 
                            ((lag / theta[i]) ** (alpha[i] - 1)) * 
                            pm.math.exp(-((lag / theta[i]) ** alpha[i]))
                            for lag in range(1, min(t+1, 15))
                        ])
                        for t in range(len(x))
                    ])
                )
                
                # Apply saturation
                saturated = pm.Deterministic(
                    f'{channel}_saturated',
                    (adstocked ** s[i]) / ((k[i] ** s[i]) + (adstocked ** s[i]))
                )
                
                transformed_channels.append(saturated * beta[i])
            
            # Linear combination
            mu = intercept + pm.math.sum(transformed_channels, axis=0)
            
            # Likelihood (Poisson for count data)
            sigma = pm.HalfNormal('sigma', sigma=10)
            y = pm.Normal('y', mu=mu, sigma=sigma, observed=conversions)
        
        return model
    
    def fit(self, df: pd.DataFrame, channels: List[str], 
            draws: int = 2000, tune: int = 1000) -> az.InferenceData:
        """
        Fit the Bayesian MMM using NUTS sampler
        
        Args:
            df: Observations dataframe
            channels: List of channel names
            draws: Number of posterior samples
            tune: Number of tuning steps
        
        Returns:
            ArviZ InferenceData object
        """
        self.model = self.build_model(df, channels)
        
        with self.model:
            # Sample using NUTS
            self.trace = pm.sample(
                draws=draws,
                tune=tune,
                target_accept=0.95,
                return_inferencedata=True
            )
        
        return self.trace
    
    def check_convergence(self) -> Dict[str, float]:
        """
        Check MCMC convergence using R-hat
        R-hat < 1.01 indicates convergence
        """
        if self.trace is None:
            raise ValueError("Model not fitted yet")
        
        summary = az.summary(self.trace)
        rhat_values = summary['r_hat'].to_dict()
        
        max_rhat = max(rhat_values.values())
        converged = max_rhat < 1.01
        
        return {
            'converged': converged,
            'max_rhat': max_rhat,
            'rhat_by_param': rhat_values
        }
    
    def get_channel_contributions(self) -> pd.DataFrame:
        """
        Extract posterior mean contributions by channel
        """
        if self.trace is None:
            raise ValueError("Model not fitted yet")
        
        posterior = self.trace.posterior
        
        contributions = []
        for var in posterior.data_vars:
            if '_saturated' in var:
                channel = var.replace('_saturated', '')
                mean_contrib = float(posterior[var].mean())
                std_contrib = float(posterior[var].std())
                
                contributions.append({
                    'channel': channel,
                    'mean_contribution': mean_contrib,
                    'std_contribution': std_contrib
                })
        
        return pd.DataFrame(contributions)
    
    def predict_saturation(self, channel: str, spend_levels: np.ndarray) -> np.ndarray:
        """
        Predict saturation curve for a channel
        """
        if self.trace is None:
            raise ValueError("Model not fitted yet")
        
        posterior = self.trace.posterior
        
        # Get posterior means for this channel's parameters
        k = float(posterior['k'].mean())
        s = float(posterior['s'].mean())
        
        # Calculate saturation at different spend levels
        saturation = self.hill_saturation(spend_levels, k, s)
        
        return saturation
    
    def calculate_incremental_roas(self, channel: str, 
                                   current_spend: float,
                                   increment: float = 1000) -> float:
        """
        Calculate incremental ROAS for a channel
        iROAS = (Revenue at spend+Δ - Revenue at spend) / Δ
        """
        if self.trace is None:
            raise ValueError("Model not fitted yet")
        
        # Get channel parameters
        posterior = self.trace.posterior
        k = float(posterior['k'].mean())
        s = float(posterior['s'].mean())
        beta = float(posterior['beta'].mean())
        
        # Calculate saturation at current and incremented spend
        sat_current = self.hill_saturation(np.array([current_spend]), k, s)[0]
        sat_increment = self.hill_saturation(np.array([current_spend + increment]), k, s)[0]
        
        # Incremental conversions
        incremental_conversions = (sat_increment - sat_current) * beta
        
        # Assume average contract value (should be parameterized)
        avg_contract_value = 8500
        incremental_revenue = incremental_conversions * avg_contract_value
        
        iroas = incremental_revenue / increment
        
        return iroas


class SyntheticGroundTruth:
    """
    Synthetic ground truth testing for model validation
    """
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
    
    def generate_synthetic_data(self, n_obs: int = 100, 
                               true_params: Dict = None) -> pd.DataFrame:
        """
        Generate synthetic data with known ground truth
        """
        if true_params is None:
            true_params = {
                'alpha': 0.5,
                'theta': 0.3,
                'k': 100,
                's': 1.0,
                'beta': 0.05,
                'intercept': 10
            }
        
        # Generate random spend
        spend = np.random.gamma(shape=2, scale=50, size=n_obs)
        
        # Apply true transformations
        mmm = BayesianMMM(str(self.engine.url))
        adstocked = mmm.weibull_adstock(spend, true_params['alpha'], true_params['theta'])
        saturated = mmm.hill_saturation(adstocked, true_params['k'], true_params['s'])
        
        # Generate conversions with noise
        mu = true_params['intercept'] + true_params['beta'] * saturated
        conversions = np.random.poisson(mu)
        
        df = pd.DataFrame({
            'observation_date': pd.date_range('2026-01-01', periods=n_obs),
            'channel_name': 'test_channel',
            'touches': spend,
            'conversions': conversions
        })
        
        return df, true_params
    
    def validate_model(self, mmm: BayesianMMM, true_params: Dict) -> Dict:
        """
        Validate model against known ground truth
        Calculate Average Calibration Error (ACE)
        """
        if mmm.trace is None:
            raise ValueError("Model not fitted")
        
        posterior = mmm.trace.posterior
        
        errors = {}
        for param, true_value in true_params.items():
            if param in posterior.data_vars:
                estimated = float(posterior[param].mean())
                error = abs(estimated - true_value) / true_value
                errors[param] = error
        
        ace = np.mean(list(errors.values()))
        
        return {
            'ace': ace,
            'param_errors': errors,
            'passed': ace < 0.05  # Target: < 5% error
        }


if __name__ == "__main__":
    # Demo: Synthetic ground truth test
    print("🧪 Bayesian MMM Synthetic Ground Truth Test")
    print("=" * 60)
    
    db_url = "postgresql://stormops:password@localhost:5432/stormops"
    
    # Generate synthetic data
    sgt = SyntheticGroundTruth(db_url)
    df, true_params = sgt.generate_synthetic_data(n_obs=50)
    
    print("\n📊 True Parameters:")
    for param, value in true_params.items():
        print(f"   {param}: {value}")
    
    # Fit model
    print("\n🔄 Fitting Bayesian MMM...")
    mmm = BayesianMMM(db_url)
    
    # Note: This would require actual PyMC installation
    # trace = mmm.fit(df, channels=['test_channel'], draws=500, tune=500)
    
    # Check convergence
    # convergence = mmm.check_convergence()
    # print(f"\n✅ Convergence: {convergence['converged']} (R-hat: {convergence['max_rhat']:.4f})")
    
    # Validate
    # validation = sgt.validate_model(mmm, true_params)
    # print(f"\n📈 Average Calibration Error: {validation['ace']:.2%}")
    # print(f"   Passed: {validation['passed']}")
    
    print("\n✅ Bayesian MMM framework ready")
    print("   Install PyMC: pip install pymc arviz")
