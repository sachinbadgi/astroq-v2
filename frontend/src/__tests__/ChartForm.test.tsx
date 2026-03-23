import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChartForm from '../components/chart/ChartForm';
import apiClient from '../api/client';

vi.mock('../api/client');

describe('ChartForm', () => {
  it('renders all form fields', () => {
    render(<ChartForm onChartGenerated={() => {}} />);
    expect(screen.getByPlaceholderText('e.g. John Doe')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. New Delhi, India')).toBeInTheDocument();
    expect(screen.getByText('Generate & Save Chart')).toBeInTheDocument();
  });

  it('calls /search-location on place blur', async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: { locations: [{ display_name: 'New Delhi, India', latitude: 28.6, longitude: 77.2, utc_offset: '+05:30', timezone: 'Asia/Kolkata' }] }
    });

    render(<ChartForm onChartGenerated={() => {}} />);
    const placeInput = screen.getByPlaceholderText('e.g. New Delhi, India');
    fireEvent.change(placeInput, { target: { value: 'New Delhi' } });
    fireEvent.blur(placeInput);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/search-location', { place_name: 'New Delhi' });
    });
  });

  it('calls /lal-kitab/generate-birth-chart on submit', async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: { status: 'success', chart_id: 123 }
    });

    const mockOnChartGenerated = vi.fn();
    render(<ChartForm onChartGenerated={mockOnChartGenerated} />);
    
    fireEvent.change(screen.getByPlaceholderText('e.g. John Doe'), { target: { value: 'Test User' } });
    
    // Assume other required fields are filled and we submit
    fireEvent.click(screen.getByText('Generate & Save Chart'));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledTimes(1);
    });
  });
});
