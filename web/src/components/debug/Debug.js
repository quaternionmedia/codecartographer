import m from 'mithril';
import meiosisTracer from 'meiosis-tracer';
import './tracer.css';
import './debug.css';

export const DebugNavContent = (cell) =>
  m(`div.debug`, DeviceSize(), TracerToggle(cell));

export const DeviceSize = () =>
  m(
    `p.debug__deviceSize`,
    `${Math.round(
      parseFloat(document.documentElement.style.getPropertyValue('--vh')) * 100
    )} x 
    ${Math.round(
      parseFloat(document.documentElement.style.getPropertyValue('--vw')) * 100
    )}`
  );

export const TracerToggle = (cell) =>
  m(
    `button.hide.debug__showTracer${cell.state.debug.tracer ? '.active' : ''}`,
    {
      title: 'Toggle the Meiosis Tracer',
      onclick: () => {
        cell.update({ debug: { tracer: !cell.state.debug.tracer } });
        const tracer = document.querySelector('#tracer');
        tracer.classList.toggle('hide');
        CloseNav(cell);
      },
    },
    '🀀'
  );

function CloseNav({ state, update }) {
  document
    .getElementsByClassName('nav__toggle')[0]
    .classList.remove('nav__toggle--open');
  document
    .getElementsByClassName('nav_right__toggle')[0]
    .classList.remove('nav_right__toggle--open');
  update({
    debugActive: false,
  });
}

// Debug
export const Tracer = (cells) => {
  meiosisTracer({
    selector: '#tracer',
    rows: 25,
    streams: [{ label: 'CodeCarto Stream', stream: cells }],
  });
  const tracer = document.querySelector('#tracer');
  //tracer.classList.toggle('hide');
};
