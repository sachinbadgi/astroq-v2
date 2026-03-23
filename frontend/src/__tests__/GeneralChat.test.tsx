import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import GeneralChat from '../components/chat/GeneralChat';
import apiClient from '../api/client';

vi.mock('../api/client');

describe('GeneralChat', () => {
  it('renders message list and input', () => {
    render(<GeneralChat chartData={{}} />);
    expect(screen.getByPlaceholderText('Ask the cosmos...')).toBeInTheDocument();
  });

  it('calls /ask-chart API on send', async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: { status: 'success', answer: 'The stars align for you.' }
    });

    render(<GeneralChat chartData={{}} />);
    const input = screen.getByPlaceholderText('Ask the cosmos...');
    fireEvent.change(input, { target: { value: 'Will I be rich?' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText('Will I be rich?')).toBeInTheDocument();
      expect(screen.getByText('The stars align for you.')).toBeInTheDocument();
    });
  });

  it('shows loading indicator during request', async () => {
    // Resolve slowly to check loading state
    let resolvePromise: any;
    const promise = new Promise(resolve => { resolvePromise = resolve; });
    (apiClient.post as any).mockReturnValueOnce(promise);

    render(<GeneralChat chartData={{}} />);
    const input = screen.getByPlaceholderText('Ask the cosmos...');
    fireEvent.change(input, { target: { value: 'Test query' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(screen.getByText('Consulting the stars...')).toBeInTheDocument();

    resolvePromise({ data: { status: 'success', answer: 'Done' } });
    
    await waitFor(() => {
      expect(screen.getByText('Done')).toBeInTheDocument();
    });
  });
});
