import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import RemedyPanel from '../components/remedy/RemedyPanel';
import apiClient from '../api/client';

vi.mock('../api/client');

const mockChartData = { chart_0: { planets_in_houses: { Sun: { house: 1 }, Moon: { house: 2 } } } };

describe('RemedyPanel', () => {
  it('renders planet selector tabs', () => {
    render(<RemedyPanel chartData={mockChartData} />);
    expect(screen.getByText('Sun')).toBeInTheDocument();
    expect(screen.getByText('Moon')).toBeInTheDocument();
  });

  it('renders shifting matrix table', async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        simulation_matrix: [
          { aspect: 'Wealth', baseline_health: 50, simulated_health: 70, delta: '+20%' }
        ],
        lifetime_timeline: []
      }
    });

    render(<RemedyPanel chartData={mockChartData} />);
    
    // Switch to a planet to trigger fetch
    fireEvent.click(screen.getByText('Sun'));
    fireEvent.click(screen.getByText('Shift'));

    await waitFor(() => {
      expect(screen.getByText('Wealth')).toBeInTheDocument();
      expect(screen.getByText('+20%')).toBeInTheDocument();
    });
  });

  it('switches sub-mode tabs', () => {
    render(<RemedyPanel chartData={mockChartData} />);
    expect(screen.getByText('Matrix')).toBeInTheDocument();
    expect(screen.getByText('Projection')).toBeInTheDocument();
  });
});
