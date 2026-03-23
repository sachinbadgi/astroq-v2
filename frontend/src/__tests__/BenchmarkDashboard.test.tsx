import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BenchmarkDashboard from '../components/benchmark/BenchmarkDashboard';
import apiClient from '../api/client';

vi.mock('../api/client');

describe('BenchmarkDashboard', () => {
  it('renders metric cards and loading state', () => {
    (apiClient.get as any).mockReturnValue(new Promise(() => {}));
    render(<BenchmarkDashboard />);
    expect(screen.getByText('Accuracy Hit Rate')).toBeInTheDocument();
  });

  it('renders test run table with data', async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        runs: [
          { id: '1', date: '2026-03-22', public_figure: 'Steve Jobs', event: 'Founded Apple', actual_age: 21, predicted_age: 21, status: 'HIT' },
          { id: '2', date: '2026-03-22', public_figure: 'Albert Einstein', event: 'Nobel Prize', actual_age: 42, predicted_age: 45, status: 'MISS' }
        ],
        metrics: { hit_rate: '85%', avg_offset: '+0.5 yrs', total_tested: 120 }
      }
    });

    render(<BenchmarkDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Steve Jobs')).toBeInTheDocument();
      expect(screen.getByText('Albert Einstein')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
      expect(screen.getByText('+0.5 yrs')).toBeInTheDocument();
      expect(screen.getByText('120')).toBeInTheDocument();
    });
  });

  it('handles empty test runs', async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: { runs: [], metrics: { hit_rate: '0%', avg_offset: '0 yrs', total_tested: 0 } }
    });

    render(<BenchmarkDashboard />);

    await waitFor(() => {
      expect(screen.getByText('No test iterations have been recorded yet.')).toBeInTheDocument();
    });
  });
});
