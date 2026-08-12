# Three-Class Annotation Policy

This dataset uses object-detection boxes with the class order defined in
`dataset/data.yaml`:

| ID | Class | Annotate |
| --- | --- | --- |
| 0 | `pipe burst` | The visible pipe, fitting, joint, hose, or fixture where water is actively escaping. |
| 1 | `water accumulation` | A contiguous region of standing or pooled water on a surface. |
| 2 | `water drop` | An individual airborne or visibly pendant droplet, or a compact, visually separable group of droplets. |

## General rules

- Annotate visible evidence, not an inferred leak hidden behind a wall.
- Draw the tightest axis-aligned box that contains the visible target.
- Keep every box inside the image.
- Annotate every visible target that meets the class definition, including
  multiple classes in the same image.
- A target cut off by the frame may be annotated to the image edge if enough
  is visible to identify it.
- Do not annotate mold, dry stains, reflections, shadows, wet-looking texture,
  or damaged material unless visible water meets one of the definitions above.
- Keep difficult negative images with empty label files.

## Class boundaries

### `pipe burst`

- Include the smallest visible source region that makes the escaping water
  understandable.
- Do not box an entire pipe run when only one joint or opening is leaking.
- Do not use this class for a dry pipe or for accumulated water without a
  visible source.

### `water accumulation`

- Box the visible contiguous pool, not the entire floor or room.
- Separate disconnected pools unless they clearly form one continuous region.
- A pool extending outside the frame may touch the image edge.
- Dampness, discoloration, or an old dry stain is not accumulation.

### `water drop`

- Box individual drops when they are visually separable.
- Include a droplet gathering on the underside of a pipe or fitting when it has
  a distinct rounded drop shape and is visibly about to detach.
- Do not label a generic wet patch or thin film on a pipe as a water drop.
- For dense spray where individual boxes would overlap heavily, use one tight
  box around the compact group and apply the same rule consistently.
- A continuous stream is one compact group, not dozens of artificial drops.
- Do not annotate tiny compression artifacts that cannot be identified as
  water at the image's native resolution.

## Split policy

- Keep all frames from one video in one split.
- Keep all photographs from one incident, property, or burst sequence in one
  split.
- Keep an original image and every crop, resize, or augmentation derived from
  it in one split.
- Validation and test images must not be exact or near duplicates of training
  images.

## Review checklist

Before approving an image, confirm:

1. Every box has the correct class.
2. No visible target is missing.
3. Boxes are tight and fully within the image.
4. Dense droplets follow the individual-versus-group rule.
5. The image belongs to the same split as related frames and source images.
