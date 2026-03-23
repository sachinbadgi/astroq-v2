import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import PredictionDashboard from '../components/prediction/PredictionDashboard';
import apiClient from '../api/client';

vi.mock('../api/client');

describe('PredictionDashboard', () => {

  it('renders loading skeleton initially', () => {
    (apiClient.get as any).mockReturnValue(new Promise(() => {}));
    render(<PredictionDashboard activeChartId={123} />);
    expect(screen.getByText(/Analyzing/i)).toBeInTheDocument();
  });

  it('renders planet strength bars and grammar scores on load', async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        pipeline_output: {
          predictions: [],
          enriched_planets: {
            Sun: { strength_total: 4.5, sleeping_status: 'Awake', dharmi_status: 'Normal', dhoka_graha: false, achanak_chot_active: false },
            Moon: { strength_total: 2.1, sleeping_status: 'Sleeping', dharmi_status: 'Dharmi', dhoka_graha: true, achanak_chot_active: true }
          }
        }
      }
    });

    render(<PredictionDashboard activeChartId={123} />);

    // Robust finding with regex and substring support
    expect(await screen.findByText(/Sun/)).toBeInTheDocument();
    expect(await screen.findByText(/Moo/)).toBeInTheDocument();
    expect(await screen.findByText(/4\.5\s*\/\s*6\.0/)).toBeInTheDocument();
    expect(await screen.findByText(/Sleeping/)).toBeInTheDocument();
    expect(await screen.findByText(/Dhoka\s*Graha/)).toBeInTheDocument();
  });

  it('shows predictions list with domain and event', async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        pipeline_output: {
          predictions: [
            {
              domain: 'Career',
              event_type: 'Promotion',
              confidence: 'highly_likely',
              polarity: 'benefic',
              probability: 0.85,
              peak_age: 35,
              age_window: [34, 36],
              prediction_text: 'Major leap in career expected.',
              source_planets: ['Sun', 'Jupiter'],
              remedy_applicable: false,
              remedy_hints: []
            }
          ],
          enriched_planets: {}
        }
      }
    });

    render(<PredictionDashboard activeChartId={123} />);

    // Search for text content instead of exact node match to be safe
    await waitFor(() => {
      const items = screen.getAllByText((content) => content.includes('Major leap in career expected.'));
      expect(items.length).toBeGreaterThan(0);
    }, { timeout: 3000 });

    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText(/highly likely/i)).toBeInTheDocument();
  });
  
  it('handles empty predictions gracefully', async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        pipeline_output: {
          predictions: [],
          enriched_planets: {}
        }
      }
    });

    render(<PredictionDashboard activeChartId={123} />);

    expect(await screen.findByText(/No definitive life events/i)).toBeInTheDocument();
  });
});
