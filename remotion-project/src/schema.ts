import { z } from "zod";
import { zColor } from "@remotion/zod-types";

const NewsItemSchema = z.object({
  title: z.string(),
  subtitle: z.string(),
  bgGradient: z.tuple([zColor(), zColor(), zColor()]),
});

export const VideoPropsSchema = z.object({
  headerTitle: z.string(),
  items: z.array(NewsItemSchema),
});

export type VideoProps = z.infer<typeof VideoPropsSchema>;
