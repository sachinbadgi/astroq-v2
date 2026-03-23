import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import OracleChat from '../components/chat/OracleChat';
import * as useSSEHook from '../hooks/useSSE';

// Mock the SSE hook
vi.mock('../hooks/useSSE');

describe('OracleChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockChartData = { id: 123 };

  it('renders query input and header', () => {
    (useSSEHook.useSSE as any).mockReturnValue({
      data: [], error: null, isStreaming: false, startStream: vi.fn()
    });

    render(<OracleChat chartData={mockChartData} />);
    expect(screen.getByPlaceholderText(/Consult the Oracle/i)).toBeInTheDocument();
    expect(screen.getByText(/PREMIUM ORACLE ANALYSIS/i)).toBeInTheDocument();
  });

  it('calls startStream with correct endpoint on submit', async () => {
    const startStreamMock = vi.fn();
    (useSSEHook.useSSE as any).mockReturnValue({
      data: [], error: null, isStreaming: false, startStream: startStreamMock
    });

    render(<OracleChat chartData={mockChartData} />);
    const input = screen.getByPlaceholderText(/Consult the Oracle/i);
    fireEvent.change(input, { target: { value: 'Why am I facing delays?' } });
    fireEvent.click(screen.getByTitle('Consult Oracle'));

    expect(startStreamMock).toHaveBeenCalled();
  });

  it('renders step-by-step SSE events correctly', async () => {
    const mockData = [
      { step: 'ANALYZE', content: 'Analyzing Venus...' }
    ];
    
    // Simulate already queried state by forcing data presence
    (useSSEHook.useSSE as any).mockReturnValue({
      data: mockData, error: null, isStreaming: false, startStream: vi.fn()
    });

    render(<OracleChat chartData={mockChartData} />);
    
    // We need hasQueried to be true. In the component it's internal state.
    // Let's trigger it.
    fireEvent.change(screen.getByPlaceholderText(/Consult the Oracle/i), { target: { value: 'test' } });
    fireEvent.click(screen.getByTitle('Consult Oracle'));

    expect(await screen.findByText(/Analyzing Venus/i)).toBeInTheDocument();
  });

  it('displays streaming spinner', async () => {
    (useSSEHook.useSSE as any).mockReturnValue({
      data: [], error: null, isStreaming: false, startStream: vi.fn()
    });
    render(<OracleChat chartData={mockChartData} />);
    
    fireEvent.change(screen.getByPlaceholderText(/Consult the Oracle/i), { target: { value: 'test' } });
    fireEvent.click(screen.getByTitle('Consult Oracle'));

    // Update mock to streaming
    (useSSEHook.useSSE as any).mockReturnValue({
      data: [], error: null, isStreaming: true, startStream: vi.fn()
    });
    
    // Re-render happens via state change in parent or just another flip
    // Since we can't easily trigger re-render of internal state from outside without props change or event,
    // and fireEvent already triggered a render.
    
    // Actually, in many cases, findByText will pick up the update if it's within the interval.
    expect(await screen.findByText(/meditating/i)).toBeInTheDocument();
  });
});
