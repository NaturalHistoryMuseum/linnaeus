import math

from matplotlib import pyplot as plt


def show(img):
    plt.imshow(img)
    plt.axis('off')
    plt.tight_layout()
    plt.show()


def plot_imgs(imgs, fn, ncols=3, title=True, max_size=65536):
    nrows = int(math.ceil(len(imgs) / ncols))
    h = (max(imgs, key=lambda x: x[1].shape[0])[1].shape[0] * nrows)
    w = (max(imgs, key=lambda x: x[1].shape[1])[1].shape[1] * ncols)
    if max_size > 65536:
        max_size = 65536
    if h > (max_size / 100) or w > (max_size / 100):
        adj = (max_size / 100) / max(w, h)
        w = int(w * adj)
        h = int(h * adj)
    fig, axes = plt.subplots(ncols=ncols, nrows=nrows, figsize=(w, h))

    for r in range(nrows):
        for c in range(ncols):
            i = (r * ncols) + c
            axes[r, c].axis('off')
            if i == len(imgs):
                break
            img = imgs[i]
            if title:
                axes[r, c].set_title(img[0])
            axes[r, c].imshow(img[1], cmap=img[2])
            try:
                for x, y in img[3]:
                    axes[r, c].plot(x, y, color='yellow', linewidth=3)
            except IndexError:
                pass

    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.02, top=0.95)
    fig.savefig(fn, transparent=True)
