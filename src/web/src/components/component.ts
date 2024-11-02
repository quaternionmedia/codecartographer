/*
    This is a simple wrapper around mithril's m
    that allows for a decoupling of the code base
    from mithril.

    If we ever want to switch to a
    different rendering engine, we can limit the
    changes to just this file.

    Note, this would mean that we would have to
    create methods to convert the current syntax
    to the new syntax.
*/

// import m from 'mithril';

// declare global {
//   const cp: typeof m;
// }
/* 
further future-proof, we could define a custom m 
interface that mirrors the relevant Mithril 
functionality we currently use. This could help 
us spot places where you might need to make changes 
if we ever replace the library.
*/
