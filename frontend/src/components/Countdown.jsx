import React, { useState, useEffect } from 'react';
import { getSecondsUntilNextPoll, formatCountdown } from '../utils/helpers';

export default function Countdown({ nextPollAt }) {
  const [seconds, setSeconds] = useState(getSecondsUntilNextPoll(nextPollAt));

  useEffect(() => {
    setSeconds(getSecondsUntilNextPoll(nextPollAt));

    const interval = setInterval(() => {
      const remaining = getSecondsUntilNextPoll(nextPollAt);
      setSeconds(remaining);

      // If countdown reaches 0, we might want to refresh
      if (remaining === 0) {
        // Could trigger a refresh here
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [nextPollAt]);

  return (
    <span className="font-mono text-sm text-gray-600">
      {formatCountdown(seconds)}
    </span>
  );
}
