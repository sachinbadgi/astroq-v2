# RESEARCH_PARAMS: The AutoResearch agent will modify these values.
# Goal: Optimize Lal Kitab engine performance across all 10 benchmark figures.

RESEARCH_PARAMS = {
    # 1. House Exchange (Bhav Parivartan)
    "research.parivartan_boost": 1.25,        
    "research.exchange_diffusion_bonus": 0.15,

    # 2. Probability Sigmoid
    "probability.base_k": 5.5,            
    "probability.ea_weighting": 0.12,     
    "probability.tvp_boost_factor": 1.2   # Age window boost
}
