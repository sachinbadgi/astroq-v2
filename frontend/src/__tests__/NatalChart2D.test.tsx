import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import NatalChart2D from '../components/chart/NatalChart2D';

describe('NatalChart2D component', () => {
  const mockChartData = {
    planets_in_houses: {
      "Sun": { "house": 8 },
      "Asc": { "house": 2 },
      "Jupiter": { "house": 3 },
      "Moon": { "house": 3 }
    },
    pipeline_output: {
      enriched_planets: {
        "Sun": { "house": 8, "aspects": [{ "target": "Jupiter", "relationship": "friend" }], "strength_total": 12.5 },
        "Jupiter": { "house": 3, "aspects": [], "strength_total": 8.0 },
        "Moon": { "house": 3, "aspects": [], "strength_total": 5.0 },
        "Asc": { "house": 2, "aspects": [], "strength_total": 10.0 }
      }
    }
  };

  it('renders all 12 house numbers', () => {
    render(<NatalChart2D chartData={mockChartData} />);
    for (let i = 1; i <= 12; i++) {
      expect(screen.getByTestId(`house-${i}`)).toBeDefined();
    }
  });

  it('places ASC in the correct house (House 2)', () => {
    render(<NatalChart2D chartData={mockChartData} />);
    const house2 = screen.getByTestId('house-2');
    expect(within(house2).getByText('ASC')).toBeDefined();
  });

  it('renders planet abbreviations (Su, Ju, Mo)', () => {
    render(<NatalChart2D chartData={mockChartData} />);
    expect(screen.getByText('Su')).toBeDefined();
    expect(screen.getByText('Ju')).toBeDefined();
    expect(screen.getByText('Mo')).toBeDefined();
  });

  it('handles multiple planets in one house (House 3)', () => {
    render(<NatalChart2D chartData={mockChartData} />);
    const house3 = screen.getByTestId('house-3');
    expect(within(house3).getByText('Ju')).toBeDefined();
    expect(within(house3).getByText('Mo')).toBeDefined();
  });

  it('renders aspect lines when data is present', () => {
    const { container } = render(<NatalChart2D chartData={mockChartData} />);
    const aspectPath = container.querySelector('path');
    expect(aspectPath).not.toBeNull();
  });

  it('toggles the legend panel', () => {
    render(<NatalChart2D chartData={mockChartData} />);
    expect(screen.queryByTestId('legend-panel')).toBeNull();
    
    const legendBtn = screen.getByLabelText(/Toggle Legend/i);
    fireEvent.click(legendBtn);
    
    expect(screen.getByTestId('legend-panel')).toBeDefined();
    expect(screen.getByText('Sun')).toBeDefined();
  });

  it('switches to Analysis tab and shows data', () => {
    render(<NatalChart2D chartData={mockChartData} />);
    const analysisTab = screen.getByRole('tab', { name: /Analysis/i });
    fireEvent.click(analysisTab);
    
    expect(screen.getByText('Planet')).toBeDefined();
    expect(screen.getByText('12.5')).toBeDefined(); // Sun's strength
  });

  it('renders Masnui planet with "m" abbreviation and ring', () => {
    const masnuiData = {
      planets_in_houses: {
        "Masnui Jupiter": { "house": 1, "is_masnui": true },
      },
      pipeline_output: {
        enriched_planets: {
          "Masnui Jupiter": { "house": 1, "is_masnui": true }
        }
      }
    };
    const { container } = render(<NatalChart2D chartData={masnuiData} />);
    expect(screen.getByText('mJu')).toBeDefined();
    expect(container.querySelector('ellipse')).not.toBeNull();
  });

  const MASNUI_VARIANTS = [
    { name: "Masnui Jupiter", abbr: "mJu" },
    { name: "Masnui Sun", abbr: "mSu" },
    { name: "Masnui Moon", abbr: "mMo" },
    { name: "Masnui Venus (Note: Unusual Conjunction)", abbr: "mVe" },
    { name: "Masnui Mars (Auspicious)", abbr: "mMa" },
    { name: "Masnui Mars (Malefic)", abbr: "mMa" },
    { name: "Masnui Rahu (Debilitated Rahu)", abbr: "mRa" },
    { name: "Masnui Mercury", abbr: "mMe" },
    { name: "Masnui Saturn (Like Ketu)", abbr: "mSa" },
    { name: "Masnui Saturn (Like Rahu)", abbr: "mSa" },
    { name: "Masnui Rahu (Exalted Rahu)", abbr: "mRa" },
    { name: "Masnui Ketu (Exalted Ketu)", abbr: "mKe" },
    { name: "Masnui Ketu (Debilitated Ketu)", abbr: "mKe" },
  ];

  it.each(MASNUI_VARIANTS)('renders %s abbreviation correctly as %s', ({ name, abbr }) => {
    const data = {
      planets_in_houses: { [name]: { house: 5, is_masnui: true } },
      pipeline_output: { enriched_planets: { [name]: { house: 5, is_masnui: true } } }
    };
    render(<NatalChart2D chartData={data} />);
    expect(screen.getByText(abbr)).toBeDefined();
  });
});
