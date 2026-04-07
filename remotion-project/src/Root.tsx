import React from 'react';
import { Composition } from 'remotion';
import { TimelineComposition } from './TimelineComposition';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="TimelineComposition"
        component={TimelineComposition}
        durationInFrames={150}
        fps={25}
        width={1920}
        height={1080}
        defaultProps={{ timelineData: null }}
      />
    </>
  );
};
