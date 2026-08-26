"use client";

import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Piège le focus clavier à l'intérieur d'une modale : Tab/Shift+Tab bouclent
 * entre le premier et le dernier élément focusable du conteneur, et Échap
 * ferme la modale. Sans ça, un Shift+Tab en sortie de modale atterrit sur un
 * élément masqué sous l'overlay (ex: une ligne du tableau admin), qui reste
 * activable au clavier bien que visuellement recouvert.
 *
 * `onClose` est capturé via une ref plutôt que placé dans le tableau de
 * dépendances de l'effet : les appelants passent une fonction inline
 * recréée à chaque rendu (non mémorisée), ce qui ferait re-déclencher
 * l'effet — et donc voler le focus une seconde fois — au moindre re-rendu
 * du parent pendant que la modale est ouverte (ex: une action admin
 * asynchrone qui se termine ailleurs sur la page pendant que l'utilisateur
 * tape dans un champ de la modale). La ref garantit que l'effet ne
 * s'exécute qu'au montage, tout en appelant toujours la version la plus
 * récente de `onClose` sur Échap.
 */
export function useFocusTrap(onClose: () => void) {
  const containerRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;

    const focusables = () =>
      Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));

    const first = focusables()[0];
    first?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab") return;
      const els = focusables();
      if (els.length === 0) return;
      const firstEl = els[0];
      const lastEl = els[els.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    }

    container.addEventListener("keydown", handleKeyDown);
    return () => {
      container.removeEventListener("keydown", handleKeyDown);
      if (previouslyFocused && typeof previouslyFocused.focus === "function") {
        previouslyFocused.focus();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // montage uniquement — onClose est lu via la ref, jamais une dépendance

  return containerRef;
}
